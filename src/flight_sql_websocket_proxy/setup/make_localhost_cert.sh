#!/bin/bash

mkcert -install
mkcert localhost

mv localhost.pem tls/server.crt
mv localhost-key.pem tls/server.key
