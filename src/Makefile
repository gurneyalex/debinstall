all: ldi

ldi: ldi.o

install: ldi
	install ldi /usr/bin
	adduser --system --no-create-home --group debinstall
	chown debinstall:debinstall /usr/bin/ldi
	chmod 6755 /usr/bin/ldi

clean:
	$(RM) ldi *.o *~
