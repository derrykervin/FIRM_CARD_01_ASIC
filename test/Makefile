SIM ?= icarus
FST ?= -fst
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../src

ifneq ($(GATES),yes)

PROJECT_SOURCES := $(shell python3 project_sources.py)
SIM_BUILD = sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))

else

SIM_BUILD = sim_build/gl

COMPILE_ARGS += -DGL_TEST
COMPILE_ARGS += -DFUNCTIONAL
COMPILE_ARGS += -DUSE_POWER_PINS
COMPILE_ARGS += -DSIM
COMPILE_ARGS += -DUNIT_DELAY=\#1

VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v

VERILOG_SOURCES += $(PWD)/gate_level_netlist.v

endif

COMPILE_ARGS += -I$(SRC_DIR)

VERILOG_SOURCES += $(PWD)/tb.v

TOPLEVEL = tb
COCOTB_TEST_MODULES = test

include $(shell cocotb-config --makefiles)/Makefile.sim

# Keep every original GL case while fitting the hosted6h job cap. Each child
# owns its waveform/results; the official action receives their full aggregate.
ifeq ($(GATES),yes)
ifneq ($(FIRM_GL_CHILD),1)
.DEFAULT_GOAL := firm_gl_profiles
.PHONY: firm_gl_profiles
firm_gl_profiles:
	python3 -B check_gl_profiles.py
	python3 run_gl_profiles.py
endif
endif
