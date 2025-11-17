# claudyata.github.io

# Procedimiento: ver cambios, actualizar master y hacer commit

Este guía te ayuda a:
- Ver qué tienes de nuevo
- Refrescar la rama master (o main) con la remota
- Integrar cambios en tu rama de trabajo
- Hacer push de tus cambios

## 1) Ver qué tienes nuevo (cambios no confirmados)

- Ver estado de archivos:  
  `git status`

- Historial de commits locales recientes:  
  `git log --oneline --decorate -n 5`

## 2) Refrescar master (actualizar con la rama remota)

- Asegúrate de estar en la rama principal:
  - `git checkout main`

- Actualiza la rama local con la remota:
  - `git fetch origin`
  - `git merge origin/main`  *(o usar `git pull origin main` que hace fetch+merge)*

## 3) Integrar cambios de la rama actual (si trabajas en una rama distinta)

- Guarda/commit tus cambios en la rama de trabajo:
  - `git add .`
  - `git rm file.txt`
  - `git commit -m "Tu mensaje de commit"`
  - Resolver conflictos si aparecen, luego:
  - `git rebase --continue`
- Alternativa (si prefieres merge en lugar de rebase):
  - `git merge origin/main`

## 4) Enviar (push) tus cambios al remoto

- Si trabajas en `master`/`main` y ya está actualizado:
  - `git push origin main`  *(o `master`)*

- Si usaste una rama de feature:
  - `git push origin <tu-rama>`
  - Después, crea un Pull Request / Merge Request en GitLab/GitHub.

## Notas útiles

- Si quieres empezar limpio (Advertencia: perderás cambios no guardados):  
  - `git reset --hard origin/main`  *(reemplaza `main` por `master` si corresponde)*

- Para ver diferencias específicas de un archivo:  
  - `git diff ruta/archivo`

- Para ver archivos que serán eliminados al actualizar:  
  - `git status -s`

## Notas útiles

- Si quieres empezar limpio (Advertencia: perderás cambios no guardados):  
  `git reset --hard origin/main`
- Para ver diferencias específicas de un archivo:  
  `git diff ruta/archivo`
- Para ver archivos que serán eliminados al actualizar:  
  `git status -s`