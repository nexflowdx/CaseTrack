# Serve os arquivos HTML estáticos do CaseTrack via Nginx.
# Imagem "alpine" é minúscula (~40MB) — suficiente, já que não há
# processamento de servidor nenhum aqui, só arquivos estáticos.
FROM nginx:alpine

COPY . /usr/share/nginx/html

# A raiz do site ("/") deve abrir direto a tela de login, não uma
# página índice genérica do Nginx (que não existe neste projeto).
RUN cp /usr/share/nginx/html/login.html /usr/share/nginx/html/index.html

EXPOSE 80