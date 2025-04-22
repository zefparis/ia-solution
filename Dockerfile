# Copy the application
COPY . .

# Crée le dossier logs et attribue les droits à appuser
RUN mkdir -p logs && chown -R ${APP_USER}:${APP_GROUP} logs

# Generate requirements.txt for reproducible builds
RUN pip freeze > requirements-lock.txt

# Make scripts executable
RUN chmod +x ./docker-entrypoint.sh ./wait-for-it.sh

# Change to non-root user (faire ça après avoir modifié les permissions)
USER ${APP_USER}:${APP_GROUP}
