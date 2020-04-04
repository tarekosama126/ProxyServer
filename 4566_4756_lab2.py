import sys
import os
import enum
import socket
import _thread as thread
class HttpRequestInfo(object):
    def __init__(self, client_info, method: str, requested_host: str,
                 requested_port: int,
                 requested_path: str,
                 headers: list):
        self.method = method
        self.client_address_info = client_info
        self.requested_host = requested_host
        self.requested_port = requested_port
        self.requested_path = requested_path
        self.headers = headers
    def to_http_string(self):
        line = self.method + " " + self.requested_path + " " + "HTTP/1.0" + "\r\n"
        for i in range(0, len(self.headers)):
            line += self.headers[i][0] + ": " + self.headers[i][1] + "\r\n"
        line += "\r\n"
        return line
    def to_byte_array(self, http_string):
        return bytes(http_string, "UTF-8")
    def display(self):
        print(f"Client:", self.client_address_info)
        print(f"Method:", self.method)
        print(f"Host:", self.requested_host)
        print(f"Port:", self.requested_port)
        print(f"Path:", self.requested_path)
        stringified = [": ".join([k, v]) for (k, v) in self.headers]
        print("Headers:\n", "\n".join(stringified))
class HttpErrorResponse(object):
    def __init__(self, code, message):
        self.code = code
        self.message = message
    def to_http_string(self):
        return str(self.code)+" "+self.message
        pass
    def to_byte_array(self, http_string):
        return bytes(http_string, "UTF-8")
    def display(self):
        print(self.to_http_string())
class HttpRequestState(enum.Enum):
    INVALID_INPUT = 0
    NOT_SUPPORTED = 1
    GOOD = 2
    PLACEHOLDER = -1
def entry_point(proxy_port_number):
    s = setup_sockets(proxy_port_number)
    while True:
        connection, client_address = s.accept()
        thread.start_new_thread(executor, (connection, client_address,))
def executor(connection, client_address):
    print("Proxy is created with :", client_address[1])
    request = ""
    while True:
        x = connection.recv(64).decode("UTF-8")
        request += x
        if request.endswith("\r\n\r\n"):
            break
    response = http_request_pipeline(client_address, request)
    connection.send(bytes(response, "utf-8"))
    connection.close()
def setup_sockets(proxy_port_number):
    print("Starting HTTP proxy on port:", proxy_port_number)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", proxy_port_number))
    s.listen(24)
    return s
def http_request_pipeline(source_addr, http_raw_data):
    returned_data = ""
    state = check_http_request_validity(http_raw_data)
    if state == HttpRequestState.GOOD:
        obj = parse_http_request(source_addr, http_raw_data)
        sanitize_http_request(obj)
        request_in_string = obj.to_http_string()

        if request_in_string in cache.keys():
            print("GETT from the cache")
            return cache[request_in_string]

        request = obj.to_byte_array(request_in_string)
        returned_data = get_data_from_host(obj, request)

        if request_in_string not in cache.keys():
            print("ADD TO THE CACHEE")
            cache[request_in_string] = returned_data

    else:
        massage = ""
        code = ""
        if state == HttpRequestState.INVALID_INPUT:
            code = 400
            massage = "Bad Request"
        if state == HttpRequestState.NOT_SUPPORTED:
            code = 501
            massage = "Not Implemented"
        error = HttpErrorResponse(code, massage)
        returned_data = error.to_http_string()
    return returned_data
def parse_http_request(source_addr, http_raw_data):
    method = None
    requested_path = None
    requested_host = None
    requested_port = None
    header = []
    seprated = http_raw_data.split('\r\n')
    for i in range(1, len(seprated)):
        if len(seprated[i]) == 0:
            continue
        head1, head2 = seprated[i].split(": ")
        if head1 == "Host":
            if ":" in head2:
                requested_host = head2[:head2.find(":")]
                requested_port = head2[head2.find(":")+1:]
                head2 = head2[:head2.find(":")]
            else:
                requested_host = head2
                requested_port = 80
        tuple_req = [head1, head2]
        header.append(tuple_req)
    first_line_request = seprated[0].split(' ')
    method = first_line_request[0]
    requested_path = first_line_request[1]
    ret = HttpRequestInfo(source_addr, method, requested_host, requested_port, requested_path, header)
    return ret
def check_http_request_validity(http_raw_data) -> HttpRequestState:
    Info = get_information(http_raw_data)
    if Info[5] is False:
        return HttpRequestState.INVALID_INPUT
    elif Info[4] is False:
        return HttpRequestState.INVALID_INPUT
    elif Info[0] is False and Info[3] is False:
        return HttpRequestState.INVALID_INPUT
    elif Info[1] == "PUT" or Info[1] == "POST" or Info[1] == "HEAD":
        return HttpRequestState.NOT_SUPPORTED
    elif Info[1] != "GET":
        return HttpRequestState.INVALID_INPUT
    else:
        return HttpRequestState.GOOD
    pass
def sanitize_http_request(request_info: HttpRequestInfo):
    Host =request_info.requested_host
    Path = request_info.requested_path
    Port = request_info.requested_port
    if isabsolute(request_info.requested_path):
        line = request_info.requested_path[7:]
        if line.find(":") != -1:
            index_of_port = line.find(":")
            Host = line[:index_of_port]
            line = line[index_of_port:]
            if line.find("/") != -1:
                index_of_path = line.find("/")
                Path = line[index_of_path:]
                if Port == None:
                    Port = line[:index_of_path]
            else:
                Path="/"
                if Port == None:
                    Port = line[1:]
        else:
            if line.find("/") != -1:
                index_of_path = line.find("/")
                Host = line[:index_of_path]
                Path = line[index_of_path:]
                if Port == None:
                    Port = 80
            else:
                Host = line
                Path = "/"
                if Port == None:
                    Port = 80
        if host_isoccur(request_info.headers) is False:
            x = ("Host", Host)
            list = []
            list.append(x)
            request_info.headers = list + request_info.headers
    else:
        line = request_info.requested_path
        if line.find(":")!= -1:
            index_of_port = line.find(":")
            if line.find("/") != -1:
                index_of_path = line.find("/")
                if Port == None:
                    Port = line[index_of_port+1:index_of_path]
                Path = line[index_of_path:]
            else:
                Path = "/"
                if Port == None:
                    Port = line[index_of_port+1:]
        else:
            if line.find("/") != -1:
                index_of_path = line.find("/")
                Path = line[index_of_path:]
                if Port == None:
                    Port = 80
    request_info.requested_host = Host
    request_info.requested_port = Port
    request_info.requested_path = Path
    pass
def get_data_from_host(request_info:HttpRequestInfo,request):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((request_info.requested_host, request_info.requested_port))
    server_socket.send(request)
    x1 = server_socket.recv(4096).decode("UTF-8")
    x_total = ""
    while len(x1) != 0:
        x_total += x1
        x1 = server_socket.recv(5000).decode("UTF-8")
    server_socket.close()
    return x_total
def get_information(data):
    HostOccur = False
    method = None
    path = None
    path_state = False
    size = False
    seperated = data.split("\r\n")
    Head_validate = True
    for i in range(1, len(seperated)):
        list = seperated[i]
        if len(list) == 0:
            continue
        if list.find(": ") != -1:
            head1, head2 = list.split(": ")
            if len(head1) == 0 or len(head2) == 0:
                Head_validate = False
                break
            if head1 == "Host":
                HostOccur = True
        else:
            Head_validate = False
            break
    request = seperated[0].split(" ")
    if len(request) != 3:
        size = False
    else:
        size = True
        method, path, version = request
        check = 'HTTP/' in version
        if len(method) == 0 or len(path) == 0 or len(version) == 0:
            size = False
        elif check is False:
            size = False
        path_state = isabsolute(path)
    return [HostOccur, method, path, path_state, size, Head_validate]
def isabsolute(path):
    if path[0] == "/":
        return False
    return True
def host_isoccur(header):
    for i in range(0, len(header)):
        x = header[i]
        if x[0] == "Host":
            return True
    return False
def get_arg(param_index, default=None):
    try:
        return sys.argv[param_index]
    except IndexError as e:
        if default:
            return default
        else:
            print(e)
            print(f"[FATAL] The comand-line argument #[{param_index}] is missing")
            exit(-1)    # Program execution failed.
def check_file_name():
    script_name = os.path.basename(__file__)
    import re
    matches = re.findall(r"(\d{4}_){,2}lab2\.py", script_name)
    if not matches:
        print(f"[WARN] File name is invalid [{script_name}]")
    else:
        print(f"[LOG] File name is correct.")
def main():
    print("*" * 50)
    print(f"[LOG] Printing command line arguments [{', '.join(sys.argv)}]")
    check_file_name()
    print("*" * 50)
    # This argument is optional, defaults to 18888
    proxy_port_number = get_arg(1, 18888)
    entry_point(proxy_port_number)
if __name__ == "__main__":
    cache = {}
    main()