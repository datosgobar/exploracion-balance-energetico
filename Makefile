.PHONY: zip_output

zip_output:
	tar -c output/ | gzip > output.tar.gz


