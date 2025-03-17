Rylee Rosenberger

Web Tester

Given a URL of an existing web server, the program determines
whether or not the web server supports http2, determines any/all cookie
names, expiry times, and domains, and determines if the server is 
password protected. The program facilitates redirects on the codes
301 and 302.

Output of the program includes incremental updates on requests, 
what connections are being made, and whether or not requests are 
successful. Each response header is printed. 
A body header is printed to mark where the body would
begin, but the body is not printed to allow for simpler output.

To run the program:
python3 WebTester.py <URL>
