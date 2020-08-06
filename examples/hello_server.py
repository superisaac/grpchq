import grpc
import argparse
from concurrent import futures
from hello import hello_pb2
from hello import resp_pb2
from hello import hello_pb2_grpc

class HelloServicer(hello_pb2_grpc.HelloServicer):
    def greeting(self, request, context):
        print("greeting")
        resp = resp_pb2.GreetingResponse(
            text="echo " + request.text)
        return resp

def serve():
    parser = argparse.ArgumentParser(
        description='example hello grpc service')
    parser.add_argument('--host',
                        type=str,
                        default='[::]',
                        help='server host to listen, default localhost')
    parser.add_argument('--port',
                        type=int,
                        default=50055,
                        help='server port to listen')
    args = parser.parse_args()

    server = grpc.server(futures.ThreadPoolExecutor(
        max_workers=2))
    hello_pb2_grpc.add_HelloServicer_to_server(
        HelloServicer(), server)
    bind = f'{args.host}:{args.port}'
    print('hello server launched at', bind)
    server.add_insecure_port(bind)
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()

