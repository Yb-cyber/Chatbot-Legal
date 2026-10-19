# Freeal - Frontend Minimalista de Consultas Laborales

Interfaz web para el asistente legal y laboral de freelancers en Argentina.

## Características
- **Diseño minimalista y moderno:** Tipografía limpia (Plus Jakarta Sans), tema oscuro estilizado, microanimaciones y enfoque prioritario en la lectura de textos legales.
- **Historial persistente:** Guarda todos los mensajes y turnos anteriores en `localStorage` del navegador. Puedes recargar la página o volver días después y tus consultas seguirán allí.
- **Contexto conversacional:** Envía los turnos anteriores a la API `/query` de FastAPI para mantener coherencia en preguntas de seguimiento.
- **Renderizado Markdown:** Las citas de artículos, leyes, viñetas y formato estructurado se visualizan con claridad gracias a Marked.js.
- **Gestión de sesión:** Botón "Reiniciar" para limpiar la conversación y comenzar una nueva cuando lo desees.
- **Monitoreo de estado:** Indicador en tiempo real del estado de conexión con el backend (`/health`).

## Cómo usarlo

### Opción 1: Directo desde FastAPI
Al iniciar el backend:
```bash
uvicorn main:app --reload
```
Abre en tu navegador:
👉 **[http://localhost:8000/](http://localhost:8000/)**

### Opción 2: Como archivo estático independiente
Puedes abrir directamente el archivo `frontend/index.html` con cualquier navegador o extensión Live Server.
