#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>

#define PWD_LEN 1024
#define SEND_LEN 8192
#define RECV_LEN 1024

int main(int argc, char **argv)
{
    if (argc <= 2) {
      printf("Example usage:\n\n\t%s sockfile -m sb.noop --flags flag\n", argv[0]);
      return -1;
    }

    int s, t, len;
    struct sockaddr_un remote;

    if ((s = socket(AF_UNIX, SOCK_STREAM, 0)) == -1) {
        perror("socket");
        exit(1);
    }

    // Trying to connect

    remote.sun_family = AF_UNIX;
    strcpy(remote.sun_path, argv[1]);
    len = strlen(remote.sun_path) + sizeof(remote.sun_family);
    if (connect(s, (struct sockaddr *)&remote, len) == -1) {
        perror("connect");
        exit(1);
    }

    char msg[SEND_LEN], pwd[PWD_LEN], *c;
    int p=0;

    // Prepend cwd to arguments
    getcwd(pwd,PWD_LEN);
    for(c=pwd; *c; ++c) {
      msg[p++] = *c;
    }

    // Copy all args (but the first) to msg
    int arg;
    for(arg=2; arg < argc && p < SEND_LEN-1; ++arg) {
      msg[p++] = ' ';                       // add a space between arguments
      for(c=argv[arg]; *c; ++c) {           // copy argument #arg
        if(*c == ' ')  msg[p++] = '\\';     // escape backslash and space
        if(*c == '\\') msg[p++] = '\\';
        msg[p++] = *c;
      }
    }

    // Sending message
    if (send(s, msg, p, 0) < 0) {
      perror("send");
      return -1;
    }

    // Receiving
    char str[RECV_LEN];
    int n;
    while (n = recv(s, str, RECV_LEN, 0), n > 0) {
      str[n] = '\0';
      printf("%s", str);
    }
    fflush(stdout);

    if (n < 0) {
      perror("recv");
    }

    close(s);

    return 0;
}
