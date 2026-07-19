MARP   ?= marp
SRC    := ietf126-ffv2.md
PDF    := ietf126-ffv2.pdf
HTML   := ietf126-ffv2.html
PPTX   := ietf126-ffv2.pptx
BUILD  := .ietf126-ffv2.build.md
# Presentation date pinned to the IETF 126 slot.
DATE   := 2026-07-24
FOOTER := Tom Haynes, $(DATE) - IETF 126 - flexfiles-v2 + proxy-server

.PHONY: all pdf html pptx clean

all: pdf

pdf: $(PDF)

$(BUILD): $(SRC)
	sed -e 's/@@DATE@@/$(DATE)/g' \
	    -e 's#@@FOOTER@@#$(FOOTER)#g' \
	    $(SRC) > $(BUILD)

$(PDF): $(BUILD)
	$(MARP) $(BUILD) -o $(PDF) --allow-local-files

html: $(BUILD)
	$(MARP) $(BUILD) --html -o $(HTML)

pptx: $(BUILD)
	$(MARP) $(BUILD) -o $(PPTX)

clean:
	rm -f $(PDF) $(HTML) $(PPTX) $(BUILD)
