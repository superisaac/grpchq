from typing import Dict, Any, List, Tuple, Callable

import argparse
import importlib
import grpc

from google.protobuf.descriptor import (
    FileDescriptor,
    ServiceDescriptor,
    MethodDescriptor, FieldDescriptor,
    Descriptor, EnumDescriptor,
)

SpecType = Tuple[str, str, Callable, Any]
SpecDict = Dict[str, Tuple[Callable, Any]]

def find_service(
        pb2: Any, methname: str) -> Tuple[MethodDescriptor, str, str]:

    fd: FileDescriptor = pb2.DESCRIPTOR
    srvname, mname = methname.split('.')
    md: MethodDescriptor = fd.services_by_name[srvname].methods_by_name[mname]
    return md, srvname, mname

def make_enum(iv: str, args: Dict[str, int]) -> int:
    return args[iv]

def make_bool(iv: str) -> bool:
    if iv in ('true', 'True'):
        return True
    elif iv in ('false', 'False'):
        return False
    else:
        raise ValueError('not a boolean value')

def make_uint(iv: str) -> int:
    v = int(iv)
    if v < 0:
        raise ValueError('negative argument')
    return v

def make_bytes(iv: str) -> bytes:
    return bytes(iv, encoding='utf-8')

def field_type_display(fd: FieldDescriptor) -> str:
    if fd.type == fd.TYPE_ENUM:
        return 'enum({})'.format(','.join(
            v.name for v in fd.enum_type.values))

    for fn in dir(fd):
        if not fn.startswith('TYPE_'):
            continue
        if fd.type == getattr(fd, fn):
            return fn[5:].lower()
    return ''

def build_request(msgd: Descriptor, prefix: List[str]) -> List[SpecType]:
    specs: List[Tuple[str, str, Any, Any]] = []
    for fd in msgd.fields:
        if fd.type == fd.TYPE_MESSAGE:
            specs.extend(
                build_request(
                    fd.message_type, prefix + [fd.name]))
            continue

        loc = '.'.join(prefix + [fd.name])
        type_disp = field_type_display(fd)
        args = None
        if fd.type == fd.TYPE_ENUM:
            args = {v.name:v.number
                    for v in fd.enum_type.values}
            fn = make_enum
        elif fd.type == fd.TYPE_BOOL:
            fn = make_bool
        elif fd.type == fd.TYPE_STRING:
            fn = str
        elif fd.type in (fd.TYPE_FLOAT, fd.TYPE_DOUBLE):
            fn = float
        elif fd.type in (fd.TYPE_INT32, fd.TYPE_INT64,
                         fd.TYPE_SINT32, fd.TYPE_SINT64,
                         fd.TYPE_SFIXED32, fd.TYPE_SFIXED64):
            fn = int
        elif fd.type in (fd.TYPE_UINT32, fd.TYPE_UINT64,
                         fd.TYPE_FIXED32, fd.TYPE_FIXED64):
            fn = make_uint
        elif fd.type == fd.TYPE_BYTES:
            fn = make_bytes
        else:
            raise ValueError(
                f'invalid fd type {fd.type} of {fd.name}')
        specs.append((loc, type_disp, fn, args))
    return specs

def validate_request_args(args: List[str], specs: SpecDict) -> Tuple[List[str], str, Any]:
    vargs: List[Tuple[List[str], str, Any]] = []
    for astr in args:
        loc, value = astr.split('=', 1)
        fn, spec_args = specs[loc]
        if spec_args is None:
            newv = fn(value)
        else:
            newv = fn(value, spec_args)
        arr = loc.split('.')
        vargs.append((arr[:-1], arr[-1], newv))
    return vargs

def apply_request(req: Any, vargs: List[Tuple[List[str], str, Any]]) -> None:
    for loc, sname, v in vargs:
        obj = req
        for gname in loc:
            obj = getattr(obj, gname)
        setattr(obj, sname, v)

def main():
    parser = argparse.ArgumentParser(description='command line interface')
    parser.add_argument('module', type=str,
                        help='pb2 module')

    parser.add_argument('method', type=str,
                        help='method name, format is Service.method')

    parser.add_argument('request', type=str,
                        nargs='*',
                        help='request arguments, format is path.to.fields=value')

    parser.add_argument('-g', '--grpc_module',
                        type=str,
                        help='the grpc stub module, default is module + "_grpc"')
    
    parser.add_argument('--desc',
                        type=str,
                        default='',
                        help='describ rpc arguments')

    parser.add_argument('-c', '--connect',
                        type=str,
                        default='localhost:50055',
                        help='the grpc server address to connect')
    
    args = parser.parse_args()

    pb2 = importlib.import_module(args.module)
    md, srvname, mname = find_service(pb2, args.method)

    req_specs = build_request(md.input_type, [])
    req_spec_dicts: SpecDict = {p:(f, v) for p, d, f, v in req_specs}

    if args.desc.lower() in ('yes', 'true', '1'):
        print('Method:', md.full_name)
        print('Arguments:')
        for p, d, f, v in req_specs:
            print(' ', f'{p}=:{d}')
        return

    req_args = validate_request_args(args.request, req_spec_dicts)
    req_cls = getattr(pb2, md.input_type.name)
    req = req_cls()
    apply_request(req, req_args)
    print('Request:', md.input_type.name)
    for line in str(req).split('\n'):
        print(' ', line)

    grpc_mod_name = args.grpc_module or args.module + '_grpc'
    grpc_mod = importlib.import_module(grpc_mod_name)
    stub_cls = getattr(grpc_mod, srvname + 'Stub')
    print('stub', stub_cls)

    channel = grpc.insecure_channel(args.connect)
    stub = stub_cls(channel)
    rpc_method = getattr(stub, mname)
    print('rpc method', rpc_method)
    resp = rpc_method(req)
    print('Response:', md.output_type.name)
    for line in str(resp).split('\n'):
        print(' ', line)

if __name__ == '__main__':
    main()
