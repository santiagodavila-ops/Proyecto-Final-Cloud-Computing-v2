-- Patrón "Single Database, Multiple Schemas": un schema por tenant, misma tabla en cada uno.
-- Se ejecuta una sola vez contra la instancia RDS MySQL (cliente SQL, no desde las Lambdas).
-- Refleja lo que el código guarda: además de las columnas del documento de referencia
-- incluye area, ubicacion, modalidad y salario (validar_vacante / crear_vacante).
-- candidato_id se conserva del documento aunque el código actual no lo escribe.
-- postulaciones referencia a vacantes (clave foránea): crear primero las vacantes.

CREATE SCHEMA IF NOT EXISTS tenant_1;
CREATE SCHEMA IF NOT EXISTS tenant_2;
CREATE SCHEMA IF NOT EXISTS tenant_3;

CREATE TABLE IF NOT EXISTS tenant_1.vacantes (
  vacante_id CHAR(36) PRIMARY KEY,
  titulo VARCHAR(150) NOT NULL,
  descripcion TEXT,
  area VARCHAR(100),
  ubicacion VARCHAR(100),
  modalidad VARCHAR(20) NOT NULL DEFAULT 'presencial',
  salario DECIMAL(12,2),
  candidato_id CHAR(36),
  estado VARCHAR(30) NOT NULL DEFAULT 'abierta',
  fecha_publicacion DATETIME,
  fecha_actualizacion DATETIME
);

CREATE TABLE IF NOT EXISTS tenant_2.vacantes (
  vacante_id CHAR(36) PRIMARY KEY,
  titulo VARCHAR(150) NOT NULL,
  descripcion TEXT,
  area VARCHAR(100),
  ubicacion VARCHAR(100),
  modalidad VARCHAR(20) NOT NULL DEFAULT 'presencial',
  salario DECIMAL(12,2),
  candidato_id CHAR(36),
  estado VARCHAR(30) NOT NULL DEFAULT 'abierta',
  fecha_publicacion DATETIME,
  fecha_actualizacion DATETIME
);

CREATE TABLE IF NOT EXISTS tenant_3.vacantes (
  vacante_id CHAR(36) PRIMARY KEY,
  titulo VARCHAR(150) NOT NULL,
  descripcion TEXT,
  area VARCHAR(100),
  ubicacion VARCHAR(100),
  modalidad VARCHAR(20) NOT NULL DEFAULT 'presencial',
  salario DECIMAL(12,2),
  candidato_id CHAR(36),
  estado VARCHAR(30) NOT NULL DEFAULT 'abierta',
  fecha_publicacion DATETIME,
  fecha_actualizacion DATETIME
);

-- Postulaciones: viven en el mismo schema que las vacantes para validar la vacante con SQL.
-- titulo_vacante se conserva (copia del título al postular, como en DynamoDB).
-- Los índices reemplazan a los GSI indice_estado e indice_vacante.
CREATE TABLE IF NOT EXISTS tenant_1.postulaciones (
  postulacion_id CHAR(36) PRIMARY KEY,
  vacante_id CHAR(36) NOT NULL,
  candidato_id CHAR(36) NOT NULL,
  titulo_vacante VARCHAR(150),
  estado VARCHAR(30) NOT NULL DEFAULT 'postulado',  -- postulado, preseleccionado, entrevista, oferta, contratado, rechazado
  notas TEXT,
  fecha_postulacion DATETIME,
  fecha_actualizacion DATETIME,
  INDEX indice_estado (estado),
  INDEX indice_vacante (vacante_id),
  FOREIGN KEY (vacante_id) REFERENCES tenant_1.vacantes (vacante_id)
);

-- Postulaciones: viven en el mismo schema que las vacantes para validar la vacante con SQL.
-- titulo_vacante se conserva (copia del título al postular, como en DynamoDB).
-- Los índices reemplazan a los GSI indice_estado e indice_vacante.
CREATE TABLE IF NOT EXISTS tenant_2.postulaciones (
  postulacion_id CHAR(36) PRIMARY KEY,
  vacante_id CHAR(36) NOT NULL,
  candidato_id CHAR(36) NOT NULL,
  titulo_vacante VARCHAR(150),
  estado VARCHAR(30) NOT NULL DEFAULT 'postulado',  -- postulado, preseleccionado, entrevista, oferta, contratado, rechazado
  notas TEXT,
  fecha_postulacion DATETIME,
  fecha_actualizacion DATETIME,
  INDEX indice_estado (estado),
  INDEX indice_vacante (vacante_id),
  FOREIGN KEY (vacante_id) REFERENCES tenant_2.vacantes (vacante_id)
);

-- Postulaciones: viven en el mismo schema que las vacantes para validar la vacante con SQL.
-- titulo_vacante se conserva (copia del título al postular, como en DynamoDB).
-- Los índices reemplazan a los GSI indice_estado e indice_vacante.
CREATE TABLE IF NOT EXISTS tenant_3.postulaciones (
  postulacion_id CHAR(36) PRIMARY KEY,
  vacante_id CHAR(36) NOT NULL,
  candidato_id CHAR(36) NOT NULL,
  titulo_vacante VARCHAR(150),
  estado VARCHAR(30) NOT NULL DEFAULT 'postulado',  -- postulado, preseleccionado, entrevista, oferta, contratado, rechazado
  notas TEXT,
  fecha_postulacion DATETIME,
  fecha_actualizacion DATETIME,
  INDEX indice_estado (estado),
  INDEX indice_vacante (vacante_id),
  FOREIGN KEY (vacante_id) REFERENCES tenant_3.vacantes (vacante_id)
);
