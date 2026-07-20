MARP   ?= marp
# Presentation date pinned to the IETF 126 slot.
DATE   := 2026-07-24
FOOTER := Tom Haynes, $(DATE) - IETF 126 - flexfiles-v2 + proxy-server

# Every .md source in this dir gets built to PDF/HTML/PPTX by the
# pattern rules below.  Add a new deck by dropping its .md file next
# to this Makefile - no Makefile edit needed.
SOURCES := $(wildcard *.md)
BUILDS  := $(patsubst %.md,.%.build.md,$(SOURCES))
PDFS    := $(SOURCES:%.md=%.pdf)
HTMLS   := $(SOURCES:%.md=%.html)
PPTXS   := $(SOURCES:%.md=%.pptx)

.PHONY: all pdf html pptx clean

all: pdf

pdf:  $(PDFS)
html: $(HTMLS)
pptx: $(PPTXS)

.%.build.md: %.md
	sed -e 's/@@DATE@@/$(DATE)/g' \
	    -e 's#@@FOOTER@@#$(FOOTER)#g' \
	    $< > $@

%.pdf: .%.build.md
	$(MARP) $< -o $@ --allow-local-files

%.html: .%.build.md
	$(MARP) $< --html -o $@

%.pptx: .%.build.md
	$(MARP) $< -o $@

clean:
	rm -f $(PDFS) $(HTMLS) $(PPTXS) $(BUILDS)
