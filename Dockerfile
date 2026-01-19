# ─── Etapa 2: Build con dependencias nativas y Python ──────────────────────────
FROM public.ecr.aws/lambda/python:3.11 AS build

# Instala herramientas de compilación para dlib/OpenCV
RUN yum -y update && \
    yum install -y \
      gcc gcc-c++ make \
      cmake3 tar gzip \
      libjpeg-turbo-devel zlib-devel \
      sqlite sqlite-devel && \
    ln -s /usr/bin/cmake3 /usr/bin/cmake && \
    yum clean all

# Copia tu fichero de dependencias “pesadas”  
COPY requirements-register.txt .

# Instala solo esas librerías  
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-register.txt

# ─── Etapa final: Imagen mínima ───────────────────────────────────────────────
FROM public.ecr.aws/lambda/python:3.11

# Trae las librerías de la build  
COPY --from=build /var/lang/lib/python3.11/site-packages/ /var/lang/lib/python3.11/site-packages/
# Después de COPY --from=build /var/lang/lib/python3.11/site-packages/ ...
COPY --from=build /usr/lib64/libjpeg.* /usr/lib64/
COPY --from=build /usr/lib64/libz.*      /usr/lib64/


# Ahora copias únicamente los ficheros que importas en runtime:
COPY handlers/register_access_user.py   handlers/
COPY services/access_users_service.py    services/
COPY services/face_service.py           services/
COPY services/storage_service.py        services/
COPY repositories/access_user_repo.py    repositories/
COPY shared/models.py                   shared/
COPY shared/db.py                       shared/

# Handler por defecto  
CMD ["handlers/register_access_user.lambda_handler"]
