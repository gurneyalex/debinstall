#include <unistd.h>
#include <stdlib.h>

int main(int argc, char* argv[])
{
    int i;
    char** arguments = malloc((argc+3)*sizeof(char*));
    char *flag="-c", *script= "from debinstall import ldi; ldi.run()";
    arguments[0] = argv[0];
    arguments[1] = flag;
    arguments[2] = script;
    for(i=1; i<argc; i++){
        arguments[i+2] = argv[i];
    }
    arguments[argc+2] = (char*)NULL;
    execv("/usr/bin/python", arguments);
                       
    return 0;
}
