FROM python:3.9

RUN mkdir -p /usr/src/reference_eileen
WORKDIR /usr/src

COPY reference_eileen/requirements.txt /usr/src/reference_eileen
RUN pip install --no-cache-dir -r reference_eileen/requirements.txt

COPY reference_eileen /usr/src/reference_eileen
COPY templates.py /usr/src/



ENTRYPOINT ["python", "-m", "reference_eileen"]
