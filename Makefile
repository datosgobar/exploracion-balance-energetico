PYTHON=venv/bin/python

all: datos-sankey.tar.gz datos-publicos

datos-publicos:


# Las dos recetas siguientes fueron tomadas de
# http://blog.bottlepy.org/2012/07/16/virtualenv-and-makefiles.html

venv: venv/bin/activate

venv/bin/activate: requirements.txt
	test -d venv || virtualenv venv
	venv/bin/pip install -r requirements.txt
	touch venv/bin/activate

.PHONY: all datos-viz datos-publicos

panel.pkl: input/Datos\ Abiertos\ Series\ V2a\ Original.xlsx codigo/procesamiento_microdatos.py
	$(PYTHON) $(lastword $^) "$<" $@

datos-sankey.tar.gz: datos-sankey/
	tar -c datos-sankey/ | gzip > datos-sankey.tar.gz

datos-sankey/: panel.pkl codigo/generar_datos_anios.py
	test -d datos-sankey || mkdir datos-sankey
	$(PYTHON) $(word 2,$^) $<

clean:
	rm -f *.pkl *.tar.gz
