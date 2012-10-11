# Makefile for catalaunch, the client component of catapult
#
# Run with:
#
#	make
#	sudo make install
#
# to install to INSTALL_DIR (default /usr/local/bin)
#
# An alternative is to run:
#
#	make local_install
#
# to install to LOCAL_INSTALL_DIR (default $HOME/bin)

CC		    = gcc
CFLAGS		    = -c -Wall -O2
LDFLAGS		    =
INSTALL_DIR	    = /usr/local/bin
EXECUTABLE	    = catalaunch
LOCAL_INSTALL_DIR   = $(HOME)/bin

SRC		    = sb/catalaunch.c

OBJ		    = $(SRC:.c=.o)

all: $(SRC) $(EXECUTABLE)

.c.o :
	$(CC) $(CFLAGS) $< -o $@

$(EXECUTABLE): $(OBJ)
	$(CC) $(LDFLAGS) $(OBJ) -o $@

install: $(EXECUTABLE)
	cp $(EXECUTABLE) $(INSTALL_DIR)/$(EXECUTABLE)
	rm -rf $(OBJ)

local_install: $(EXECUTABLE)
	cp $(EXECUTABLE) $(LOCAL_INSTALL_DIR)/$(EXECUTABLE)

clean:
	rm -rf $(OBJ)
