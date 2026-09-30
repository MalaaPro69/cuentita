# cuentita
Cuentita es una app web para llevar un registro de tus ingresos, salidas e inversiones en tu dìa a dìa. Cuentita integra una ia la cual analiza el texto que ingresas sobre un gasto y lo registra automaticamente.

## Base de datos

Los cambios de esquema se gestionan con Alembic. Ejecuta las migraciones antes de iniciar la aplicación, desde la carpeta `Cuentita`:

```powershell
..\venv\Scripts\python.exe -m alembic upgrade head
..\venv\Scripts\python.exe -m uvicorn main:app --reload
```

Para una base nueva, `alembic upgrade head` crea el esquema completo. Para adoptar una base existente, detén la aplicación, haz una copia de seguridad, confirma que `DATABASE_URL` apunta a esa base y que su esquema coincide con la revisión `88082bcca661`; luego ejecuta:

```powershell
..\venv\Scripts\python.exe -m alembic stamp 88082bcca661
..\venv\Scripts\python.exe -m alembic upgrade head
```

La migración final exige que cada gasto tenga un usuario y se detiene si encuentra gastos huérfanos. También retira dos columnas antiguas de inversiones solo si están vacías. No ejecutes `stamp` sobre una base distinta ni sin copia de seguridad; detén Uvicorn mientras apliques cambios a una SQLite en uso.
