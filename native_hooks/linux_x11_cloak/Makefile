CC = gcc
CFLAGS = -Wall -fPIC -O2
LDFLAGS = -shared -ldl -lX11 -lXext

all: libstealthcloak.so

libstealthcloak.so: libstealthcloak.c
	$(CC) $(CFLAGS) libstealthcloak.c $(LDFLAGS) -o libstealthcloak.so

clean:
	rm -f libstealthcloak.so
