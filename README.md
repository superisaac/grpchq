# grpchq
Projects and utilities related to gRPC in python

# install
```shell
pip install git+https://github.com/superisaac/grpchq.git
```

# examples
## command line gRPC client

```shell
# show argument description
% grpc-call hello.hello_pb2 Hello.greeting --desc yes
Method: hello.Hello.greeting
Arguments:
  text=:string
  num=:int64
  m_type=:enum(ZERO,ONE,TWO)
  sub_msg.text=:string
  sub_msg.num=:int32
  kernel=:string
  signal=:uint32

# call remote gRPC server
% grpc-call hello.hello_pb2 Hello.greeting text=joke sub_msg.num=163 m_type=TWO -c localhost:50055
Request: GreetingRequest
  text: "joke"

Response: GreetingResponse
  text: "echo joke"
```
