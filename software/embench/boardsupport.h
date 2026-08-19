/* boardsupport.h — Embench-IoT Board Support for RV32 OoO Core */
#ifndef BOARDSUPPORT_H
#define BOARDSUPPORT_H

#include <stdint.h>

void initialise_board(void);
void start_trigger(void);
void stop_trigger(void);

#endif /* BOARDSUPPORT_H */
