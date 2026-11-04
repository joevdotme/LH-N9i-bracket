PYTHON ?= python3
export PYTHONPATH := src:$(PYTHONPATH)

CHIPSET ?= lga115x
COOLER ?= nh-l9i
OUT ?= build

.PHONY: bracket brackets test

ARGS := --chipset $(CHIPSET) --cooler $(COOLER) --out $(OUT)
ifneq ($(CENTER),)
ARGS += --center $(CENTER)
endif
ifneq ($(SPAN),)
ARGS += --span $(SPAN)
endif
ifneq ($(SPAN_X),)
ARGS += --span-x $(SPAN_X)
endif
ifneq ($(SPAN_Y),)
ARGS += --span-y $(SPAN_Y)
endif
ifneq ($(ORTHOGONAL),)
ARGS += --orthogonal $(ORTHOGONAL)
endif
ifneq ($(THICKNESS),)
ARGS += --thickness $(THICKNESS)
endif

bracket:
	$(PYTHON) -m bracketlab build $(ARGS)

brackets:
	$(MAKE) bracket CHIPSET=lga115x CENTER= SPAN= SPAN_X= SPAN_Y= ORTHOGONAL= THICKNESS=
	$(MAKE) bracket CHIPSET=hp-microserver-gen8 CENTER= SPAN= SPAN_X= SPAN_Y= ORTHOGONAL= THICKNESS=

test:
	$(PYTHON) -m pytest -q
