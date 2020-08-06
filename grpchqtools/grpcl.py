"""
A console tool to call gRPC method from command line arguments
Usage: grpcl <pb2module> <method> args
"""
# pylint: disable=missing-function-docstring
# pylint: disable=too-many-locals

from typing import Dict, Any, List, Tuple, Callable
import re
import argparse
import importlib
import grpc

from google.protobuf.descriptor import (
    FileDescriptor,
    MethodDescriptor, FieldDescriptor,
    Descriptor
)

SpecType = Tuple[str, str, Callable, Any]
SpecDict = Dict[str, Tuple[Callable, Any]]

def find_msg_cls(msg: Descriptor) -> Any:
    file_desc = msg.file
    modpath = re.sub(r'\.proto$', '_pb2', file_desc.name).replace('/', '.')
    mod = importlib.import_module(modpath)
    return getattr(mod, msg.name)

def find_service(
        pb2: Any, methname: str) -> Tuple[MethodDescriptor, str]:

    file_desc: FileDescriptor = pb2.DESCRIPTOR
    srvname, mname = methname.split('.')
    srvd = file_desc.services_by_name[srvname]
    mdesc: MethodDescriptor = srvd.methods_by_name[mname]
    return mdesc, srvd

def make_enum(inputv: str, args: Dict[str, int]) -> int:
    return args[inputv]

def make_bool(inputv: str) -> bool:
    if inputv in ('true', 'True'):
        return True
    if inputv in ('false', 'False'):
        return False
    raise ValueError('not a boolean value')

def make_uint(inputv: str) -> int:
    value = int(inputv)
    if value < 0:
        raise ValueError('negative argument')
    return value

def make_bytes(inputv: str) -> bytes:
    return bytes(inputv, encoding='utf-8')

def field_type_display(file_desc: FieldDescriptor) -> str:
    if file_desc.type == file_desc.TYPE_ENUM:
        return 'enum({})'.format(','.join(
            v.name for v in file_desc.enum_type.values))

    for func_name in dir(file_desc):
        if not func_name.startswith('TYPE_'):
            continue
        if file_desc.type == getattr(file_desc, func_name):
            return func_name[5:].lower()
    return ''

def build_request(msgd: Descriptor, prefix: List[str]) -> List[SpecType]:
    specs: List[Tuple[str, str, Any, Any]] = []
    for file_desc in msgd.fields:
        if file_desc.type == file_desc.TYPE_MESSAGE:
            specs.extend(
                build_request(
                    file_desc.message_type, prefix + [file_desc.name]))
            continue

        loc = '.'.join(prefix + [file_desc.name])
        type_display = field_type_display(file_desc)
        args = None
        if file_desc.type == file_desc.TYPE_ENUM:
            args = {v.name:v.number
                    for v in file_desc.enum_type.values}
            func = make_enum
        elif file_desc.type == file_desc.TYPE_BOOL:
            func = make_bool
        elif file_desc.type == file_desc.TYPE_STRING:
            func = str
        elif file_desc.type in (file_desc.TYPE_FLOAT, file_desc.TYPE_DOUBLE):
            func = float
        elif file_desc.type in (
                file_desc.TYPE_INT32, file_desc.TYPE_INT64,
                file_desc.TYPE_SINT32, file_desc.TYPE_SINT64,
                file_desc.TYPE_SFIXED32, file_desc.TYPE_SFIXED64):
            func = int
        elif file_desc.type in (
                file_desc.TYPE_UINT32, file_desc.TYPE_UINT64,
                file_desc.TYPE_FIXED32, file_desc.TYPE_FIXED64):
            func = make_uint
        elif file_desc.type == file_desc.TYPE_BYTES:
            func = make_bytes
        else:
            raise ValueError(
                f'invalid file descriptor type {file_desc.type} of {file_desc.name}')
        specs.append((loc, type_display, func, args))
    return specs

def validate_request_args(args: List[str], specs: SpecDict) -> Tuple[List[str], str, Any]:
    vargs: List[Tuple[List[str], str, Any]] = []
    for astr in args:
        loc, value = astr.split('=', 1)
        func, spec_args = specs[loc]
        if spec_args is None:
            newv = func(value)
        else:
            newv = func(value, spec_args)
        arr = loc.split('.')
        vargs.append((arr[:-1], arr[-1], newv))
    return vargs

def apply_request(req: Any, vargs: List[Tuple[List[str], str, Any]]) -> None:
    for loc, sname, value in vargs:
        obj = req
        for gname in loc:
            obj = getattr(obj, gname)
        setattr(obj, sname, value)

def parse_args():
    parser = argparse.ArgumentParser(description='command line interface')
    parser.add_argument('module', type=str,
                        help='pb2 module')

    parser.add_argument('method', type=str,
                        help='method name, format is Service.method')

    parser.add_argument('request', type=str,
                        nargs='*',
                        help='request arguments, format is path.to.fields=value')

    parser.add_argument('--desc',
                        type=str,
                        default='',
                        help='describ rpc arguments')

    parser.add_argument('-c', '--connect',
                        type=str,
                        default='localhost:50055',
                        help='the grpc server address to connect')

    return parser.parse_args()

def main():
    args = parse_args()
    pb2 = importlib.import_module(args.module)
    mdesc, srvd = find_service(pb2, args.method)

    req_specs = build_request(mdesc.input_type, [])
    req_spec_dicts: SpecDict = {p:(f, v) for p, d, f, v in req_specs}

    if args.desc.lower() in ('yes', 'true', '1'):
        print('Method:', mdesc.full_name)
        print('Arguments:')
        for loc, type_display, _, _ in req_specs:
            print(' ', f'{loc}=:{type_display}')
        return

    req_args = validate_request_args(args.request, req_spec_dicts)

    req_cls = find_msg_cls(mdesc.input_type)
    resp_cls = find_msg_cls(mdesc.output_type)

    req = req_cls()
    apply_request(req, req_args)

    print('Request:', mdesc.input_type.name)
    for line in str(req).split('\n'):
        print(' ', line)

    # TODO: support secure channel
    channel = grpc.insecure_channel(args.connect)

    rpc_method = channel.unary_unary(
        f'/{srvd.full_name}/{mdesc.name}',
        request_serializer=req_cls.SerializeToString,
        response_deserializer=resp_cls.FromString)

    resp = rpc_method(req)
    print('Response:', mdesc.output_type.name)
    for line in str(resp).split('\n'):
        print(' ', line)

if __name__ == '__main__':
    main()
