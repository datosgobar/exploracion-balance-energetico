PYTHON=/home/gonzalo/anaconda2/envs/energia/bin/python
	 
.PHONY: all
	
.INTERMEDIATE: panel.pkl
	
all: output.tar.gz
	
panel.pkl: input/Datos\ Abiertos\ Series\ V2a\ Original.xlsx procesamiento_microdatos.py
	$(PYTHON) $(lastword $^) "$<" $@
	
output.tar.gz: data
	tar -c output/ | gzip > output.tar.gz
		 
data: panel.pkl generar_datos_anios.py
	$(PYTHON) $(word 2,$^) $<
	 
clean:
	rm -f *.pkl *.tar.gz
