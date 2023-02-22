# DNS to DNS-over-TLS proxy

---

## Implementation

Python 3.8.9
Dependencies: socket, socketserver, ssl, threading, logging

The application is a proxy between regular DNS client and DNS-over-TLS (DoT).
For incoming messages `socketserver` lib is used with `ThreadingMixIn` to allow multiple connections at the same time.
Application can work in 2 modes:
- `tcp` - server listens for incoming TCP connections
- `udp` - server listens for incoming UDP connections
In order to select mode, provide `PROTO` environment variable (see run options below).

### How it works

The app starts a server and waits for incoming messages. For each new request an additional thread is created in
order to allow multiple simultaneous requests. When handling a request, 2 similar workflows can be executed
depending on which mode of app is launched:
- `tcp` - app receives a DNS message from client over TCP, establises a TLS-encrypted connection to DoT server,
sends received message to DoT server, receives response and sends it back to initial client over TCP.
- `udp` - app receives a DNS message from client, adds 2 length bytes in the beggining of the message,
establishes TLS-encrypted connection to DoT server, sends received message to DoT server, receives response and sends
it back to initial client over UDP.

This is needed as TLS connection is only available over TCP and according to [RFC-1035](https://www.rfc-editor.org/rfc/rfc1035#section-4.2.2)
UDP vs TCP usage.

To me it seemed that this proxy should be totally stateless and just forward messages to and from, so no checking of 
message contents is implemented.

### Running application

Application can be configured by providing the following environment variables:
- `BIND_ADDRESS` - bind address for application, IPv4 address (default: `0.0.0.0`)
- `BIND_PORT` - bind port for application, int (default: `53`)
- `PROTO` - which protocol to use when receiving requests, `tcp | udp` (default: `udp`)
- `DOT_ADDRESS` - address of DoT server, IPv4 address (default: `1.1.1.1` (Cloudflare))
- `DOT_PORT` - port of DoT server, int (default: `853`)
- `LOG_LEVEL` - log level, `info | debug` (default: `info`)

#### Local

Run:
```shell
python3 [KEY=VAL] proxy.py
```

#### Docker

Build:
```shell
docker build -t <your-tag> .
```

Run:
```shell
docker run -d --rm --name <your-name> \
  -p <port>:53 \
  [-e KEY=VAL] \
  <your-tag>
```

### Testing

```shell
kdig google.com @127.0.0.1:<port> [+tcp]
```

---

## Deploying in infrastructure: security concerns

- DNS messages are sent to Proxy are still in plaintext, so still susceptible to man-in-the-middle attack.
- DoT server certificate should be periodically verified

## Integration solution in  distributed, microservice-oriented and containerized architecture

This proxy is completely stateless so it can be deployed with multiple instances to be fail proof (e.g. Kubernetes Deployment or DaemonSet).
It is also possible to conifigure Kubernetes to inject this DNS proxy to `/etc/resolv.conf` of other pods. If a service mesh
is used in the cluster, sidecar proxies can intercept regular DNS requests and reroute them to DNS proxy. Usage of a service
mesh will also allow to do service discovery.
As the proxy is implemented in a way that it handles TCP OR UDP, one at a time, it would make sense to have a fleet of TCP proxies
and a fleet of UDP proxies.

## Possible improvements

- Considering [RFC-7858](https://www.rfc-editor.org/rfc/rfc7858), TLS connection should be reused as much as possible
to avoid TCP and TLS handshake overhead. So refactoring of code in order to have one connection as long as possible
- Connected to the previous one, before  sending request to DoT, checking that connection is still alive and recreating it
if connection is lost
- Implement retries in case of DoT server is unavailable
- Verify DoT server certificate
- Intoduce metrics gathering (e.g. for Prometheus). Possible metrics can include CPU, RAM usage, total number of requests,
number of errors
- Support IPv6
- Implement command line arguments in addition to environment variables
- Allow logging to file
- Caching (I not sure whether it is needed, as DNS client is also doing some caching). TTL can be extracted from the response.
- Cover more code with exception handling
