import sys
import socket
import ssl
import re

HTTP_PORT = 80
HTTPS_PORT = 443

BUFFER_SZ = 100000

http2 = False
password = 'no'

def parse_uri(uri: str):
    """
    doesnt have ://, add http://
    split into protocol and rest by "://"
    get host and path if there's a /
    add / to front of path
    if path empty then path = '/'
    if no www. then add it to host"""
    
    if "://" not in uri:
        uri = "http://" + uri

    #regular expression to match the URI and capture the components
    regex = r'^(?P<protocol>[a-zA-Z][a-zA-Z\d+\-.]*):\/\/(?P<host>[^:/\s]+)(?::(?P<port>\d+))?(?P<path>\/[^\s]*)?$'
    
    match = re.match(regex, uri)
    
    if match:
        protocol = match.group('protocol')
        host = match.group('host')
        port = match.group('port') if match.group('port') else None  # Port is optional
        path = match.group('path') if match.group('path') else '/'  # Default to '/' if no path is provided
        return protocol, host, port, path
    else:
        raise ValueError(f"Invalid URI format: {uri}")

def check_code(code: str, header_lines: list, path:str) -> None:
    global password
    
    if code == '200':
        return
    
    elif code == '401':
        #webpage is password protected
        password = 'yes'
    
    elif code == '301' or code == '302':
        #redirection required
        location = None
        for line in header_lines:
            if line.lower().startswith("location:"):
                location = line.split(":", 1)[1].strip()
                break
        if location:
            print(f"Redirecting to {location}")
            protocol, host, port, path = parse_uri(location)
            if protocol == "http":
                options_request(host, path)
            else:
                tls_handshake(host, path)
            return
        else:
            print(f"Unable to redirect. Exiting program")
            exit()
    
    elif code[0] == '5':
        print(f"Error code {code}: Server error. Exiting program.")
        exit()
    
    elif code[0] == '4':
        print(f"Error code {code}: Client error. Exiting program.")
        exit()
    #how many cases to handle?
    return

def print_cookies(header_lines: str):
    print(f"2. List of Cookies:")
    
    for line in header_lines:
        
        if line.lower().startswith("set-cookie:"):
            line = line[len("Set-Cookie:"):].strip()
            cookie_info = line.split("; ")
            
            cookie_name = cookie_info[0].split("=")[0]
            domain_name = None
            expiry = None

            for info in cookie_info[1:]:
                if info.startswith("expires="):
                    expiry = info.split("=")[1]
                
                elif info.startswith("domain="):
                    domain_name = info.split("=")[1]

            print(f"cookie name: {cookie_name}", end="")
            
            if expiry:
                print(f", expires time: {expiry}", end="")
            
            if domain_name:
                print(f", domain name: {domain_name}", end="")
            
            print()
    return


def analyze_response(response: str, host: str, path: str):
    global password
    if "\r\n\r\n" in response:
        header, body = response.split("\r\n\r\n", 1)
    else:
        header = response
    header_lines = header.split("\r\n")
    status_line = header_lines[0]

    version, code, phrase = status_line.split(' ', 2)

    #check code to see if further redirects are required
    code.strip()
    if code in ('301', '302'):
        check_code(code, header_lines, path)
        return
    else:
        check_code(code, header_lines, path)
    
    #start output of final results
    print("--Results--")
    print(f"website: {host}")
    
    #output HTTP2 support
    if http2:
        print(f"1. Supports http2: yes")
    else: 
        print(f"1. Supports http2: no")

    #get/print cookies
    print_cookies(header_lines)

    #print password info
    print(f"3. Password protected: {password}")

def print_response(response: str):

    #split at the head/body seperator if there is head and body
    if "\r\n\r\n" in response:
        header, body = response.split("\r\n\r\n", 1)
        print("--Response Header--")
        print(header)

        print("\n--Response Body--\n... (truncated)\n")
    else:
        print("--Response Header--")
        print(response)
        print()


def tls_handshake(host: str, path: str):
    global http2
    #default context

    context = ssl.create_default_context()
    context.set_alpn_protocols(['http/1.1', 'h2'])
    
    #create TCP socket and wrap with SSL
    conn = context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=host)

    #make connection
    conn.connect((host, HTTPS_PORT)) 
    print(f"Connected to {host} with SSL")
    
    #negotiate protocol
    protocol = conn.selected_alpn_protocol()
    print(f"ALPN Negotiated Protocol: {protocol}\n")
    
    #close connection
    conn.close()

    #create new ssl connection without alpn protocols
    context_no_alpn = ssl.create_default_context()
    conn = context_no_alpn.wrap_socket(socket.socket(socket.AF_INET), server_hostname=host)
    conn.connect((host, HTTPS_PORT))

    request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    print("--Request begin--")
    print(request)
    #send request
    conn.send(request.encode()) 
    #receive response
    response = conn.recv(BUFFER_SZ) 
    print("--Request end--\n")
    

    print(f"HTTPS request sent, waiting for response...\n")
    
    response = response.decode()
    print_response(response)
        
    analyze_response(response, host, path)

    #close connection
    conn.close()
    return
    


def options_request(host: str, path: str):
    global http2

    #format the request string as specified in tutorial to use with s.send
    request = f"OPTIONS {path} HTTP/1.1\r\n"
    request += f"Host: {host}\r\n"
    request += f"Connection: keep-alive\r\n"
    request += f"Upgrade: h2c\r\n"  # Upgrade to HTTP/2 (cleartext, h2c)
    request += f"Accept: */*\r\n"
    request += f"\r\n"

    print("--Request begin--")
    print(request)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #make connection
    s.connect((host, HTTP_PORT))
    #send request
    s.send(request.encode()) #use .encode() to convert from str to a bytes object
    #receive response
    response = s.recv(BUFFER_SZ) 
    s.close()
    print("--Request end--\n")

    print(f"HTTP options request sent, waiting for response...")
    response = response.decode()

    #check if "HTTP2-Settings" line is in response
    if "HTTP2" in response:
        print(f"--Response Header--")
        print_response(response)
        http2 = True
        analyze_response(response, host, path)
    else:
        print(f"HTTP options request failed. Attempting HTTPS TLS.\n")
        tls_handshake(host, path)

    return


def main():

    # Check that URI was passed at runtime
    if len(sys.argv) < 2:
        print(f"Error: no URI passed.\nUsage: WebTester.py <URI>")
        return

    uri = sys.argv[1]
    protocol, host, port, path = parse_uri(uri)
    
    if protocol == 'http':
        options_request(host, path)
    
    elif protocol == 'https':
        tls_handshake(host, path)
    
    
    #move inner function calls to main ?
    

    

# Execute main
if __name__ == "__main__":
    main()