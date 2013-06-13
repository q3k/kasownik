import readline
import code
import requests
import hmac
import json


class APIClient(object):
    def __init__(self, key, address="https://fascist.hackerspace.pl"):
        self.key = key
        self.address = address.rstrip("/")

    def __getattr__(self, name):
        def f(data={}):
            serialized = json.dumps(data)
            mac = hmac.new(self.key)
            mac.update(serialized)
            mac64 = mac.digest().encode("base64")
            data = serialized.encode("base64") + "," + mac64
            r = requests.post("%s/%s" % (self.address, name), data)
            return r
        return f

if __name__ == "__main__":
    # invoke an interactive version
    client = APIClient("testkey", "http://127.0.0.1:5000")
    vars = globals().copy()
    vars.update(locals())
    shell = code.InteractiveConsole(vars)
    shell.interact()
