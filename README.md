# grpchq
Projects and utilities related to gRPC in python

# Install
```shell
pip install git+https://github.com/superisaac/grpchq.git
```

# Examples
## command line gRPC client
```shell
% grpc-cl hello.hello_pb2 Hello.greeting text=joke -c localhost:50055
Request: GreetingRequest
  text: "joke"

Response: GreetingResponse
  text: "echo joke"
```
