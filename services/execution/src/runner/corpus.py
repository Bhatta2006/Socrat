"""Malicious programs are inert data until the dedicated gVisor gate is invoked."""

from typing import Literal

SOURCES = {
    "python": {
        "semantic": "print(int(input()) * 2)",
        "cpu": "while True: pass",
        "memory": "x=[]\nwhile True: x.append(bytearray(1024*1024))",
        "output": "while True: print('x'*4096, flush=True)",
        "disk": "open('/work/flood','wb').write(b'x'*(40*1024*1024))",
        "fork": "import os\nwhile True:\n if os.fork()==0:\n  while True: pass",
        "timing": "import time\ntime.sleep(60)",
        "probes": """import os, socket, subprocess
assert os.getuid() == 10001
assert not any('SECRET' in x or 'TOKEN' in x or 'PASSWORD' in x for x in os.environ)
for path in ['/run/secrets', '/var/run/docker.sock', '/host']:
 assert not os.path.exists(path)
try:
 open('/outside','w').write('escape')
 raise AssertionError('writable root')
except OSError: pass
try:
 socket.create_connection(('1.1.1.1',443), timeout=1)
 raise AssertionError('egress')
except OSError: pass
assert subprocess.check_output(['/usr/local/bin/python3','-I','-c','print(7)']).strip() == b'7'
print('isolated')""",
    },
    "cpp": {
        "semantic": "#include <iostream>\nint main(){long long n;std::cin>>n;std::cout<<n*2;}",
        "cpu": 'int main(){for(;;){asm volatile("");}}',
        "memory": '#include <cstdlib>\n#include <cstring>\nint main(){for(;;){auto p=malloc(1024*1024);if(!p)return 1;memset(p,1,1024*1024);asm volatile(""::"r"(p):"memory");}}',
        "output": "#include <iostream>\n#include <string>\nint main(){for(;;)std::cout<<std::string(4096,'x')<<std::flush;}",
        "disk": "#include <fstream>\n#include <string>\nint main(){std::ofstream f(\"/work/flood\");for(int i=0;i<40;i++)f<<std::string(1024*1024,'x');return f.good()?0:1;}",
        "fork": "#include <unistd.h>\nint main(){for(;;)if(fork()==0)for(;;){}}",
        "timing": "#include <unistd.h>\nint main(){sleep(60);}",
        "probes": """#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <cstdlib>
#include <cstring>
#include <iostream>
extern char **environ;
int main(){if(getuid()!=10001)return 1;
for(char** p=environ;*p;p++)if(strstr(*p,"SECRET")||strstr(*p,"TOKEN")||strstr(*p,"PASSWORD"))return 2;
for(auto p:{"/run/secrets","/var/run/docker.sock","/host"})if(access(p,F_OK)==0)return 3;
int fd=open("/outside",O_WRONLY|O_CREAT,0600);if(fd>=0)return 4;
int s=socket(AF_INET,SOCK_STREAM,0);sockaddr_in a{};a.sin_family=AF_INET;a.sin_port=htons(443);inet_pton(AF_INET,"1.1.1.1",&a.sin_addr);
if(connect(s,(sockaddr*)&a,sizeof(a))==0)return 5;
if(system("/bin/true")!=0)return 6;std::cout<<"isolated";}""",
    },
    "java": {
        "semantic": "long n=new java.util.Scanner(System.in).nextLong();System.out.println(n*2);",
        "cpu": "while(true){}",
        "memory": "var x=new java.util.ArrayList<byte[]>();while(true)x.add(new byte[1024*1024]);",
        "output": 'while(true)System.out.print("x".repeat(4096));',
        "disk": 'java.nio.file.Files.write(java.nio.file.Path.of("/work/flood"),new byte[40*1024*1024]);',
        "fork": 'while(true)new ProcessBuilder("/bin/sleep","60").start();',
        "timing": "Thread.sleep(60000);",
        "probes": """for(String k:System.getenv().keySet())if(k.contains("SECRET")||k.contains("TOKEN")||k.contains("PASSWORD"))throw new Exception("secret");
for(String p:new String[]{"/run/secrets","/var/run/docker.sock","/host"})if(java.nio.file.Files.exists(java.nio.file.Path.of(p)))throw new Exception("mount");
try{java.nio.file.Files.writeString(java.nio.file.Path.of("/outside"),"escape");throw new Exception("writable root");}catch(java.io.IOException expected){}
try{var s=new java.net.Socket();s.connect(new java.net.InetSocketAddress("1.1.1.1",443),1000);throw new Exception("egress");}catch(java.io.IOException expected){}
if(new ProcessBuilder("/bin/true").start().waitFor()!=0)throw new Exception("subprocess");System.out.println("isolated");""",
    },
}


def source(language: Literal["python", "cpp", "java"], case: str):
    value = SOURCES[language][case]
    if language == "java":
        return (
            "public class Solution{public static void main(String[] a)throws Exception{"
            + value
            + "}}"
        )
    return value
