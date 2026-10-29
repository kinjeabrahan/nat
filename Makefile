CC = cc
PYTHON ?= python3
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -O2
SAN_CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -g -O1 -fno-omit-frame-pointer -fsanitize=address,undefined
# Non-PIE avoids ASan shadow-address conflicts in some Linux containers.
SAN_NO_PIE ?= $(shell test "$$(uname -s)" = Linux && printf '%s' '-fno-pie -no-pie')
ASAN_OPTIONS ?= detect_leaks=1:halt_on_error=1
UBSAN_OPTIONS ?= halt_on_error=1

.PHONY: all test test-sanitize benchmark clean
all: build/nat

build:
	mkdir -p build

build/nat: nat.c legacy_lex.h | build
	$(CC) $(CFLAGS) $< -o $@

build/nat-sanitize: nat.c legacy_lex.h | build
	$(CC) $(SAN_CFLAGS) $(SAN_NO_PIE) $< -o $@

test: build/nat
	$(PYTHON) tests/test_nat.py --nat build/nat
	$(PYTHON) -m unittest discover -s tests -p test_compiler.py -v
	$(PYTHON) -m unittest discover -s tests -p test_functions.py -v
	$(PYTHON) -m unittest discover -s tests -p test_source_tool.py -v

test-sanitize: build/nat-sanitize
	ASAN_OPTIONS='$(ASAN_OPTIONS)' UBSAN_OPTIONS='$(UBSAN_OPTIONS)' $(PYTHON) tests/test_nat.py --nat build/nat-sanitize

benchmark:
	$(PYTHON) benchmarks/run.py --output build/benchmark.json

clean:
	rm -rf build

.PHONY: test-compiler native-example benchmark-native
test-compiler:
	$(PYTHON) -m unittest discover -s tests -p test_compiler.py -v

native-example: | build
	$(PYTHON) -m natc build examples/compiled/suma.nat -o build/suma

benchmark-native:
	$(PYTHON) benchmarks/native_run.py --output build/native-benchmark.json

.PHONY: test-functions
test-functions:
	$(PYTHON) -m unittest discover -s tests -p test_functions.py -v

.PHONY: source-tool
source-tool: | build
	$(PYTHON) -m natc build herramientas/nat_fuente.nat --backend asm -o build/nat-fuente
