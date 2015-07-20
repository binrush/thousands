CREATE TABLE IF NOT EXISTS ridges (
    id smallint PRIMARY KEY,
    name varchar NOT NULL,
    description text,
    color varchar(6)
);

CREATE TABLE IF NOT EXISTS summits (
    id serial PRIMARY KEY,
    rid smallint REFERENCES ridges,
    name varchar,
    name_alt varchar,
    height smallint NOT NULL,
    description text,
    lng double precision NOT NULL,
    lat double precision NOT NULL
);

CREATE TABLE IF NOT EXISTS images (
    id serial PRIMARY KEY,
    type varchar(256),
    payload bytea
);

CREATE TABLE IF NOT EXISTS users (
    id serial PRIMARY KEY,
    oauth_id varchar(256) NOT NULL,
    src smallint NOT NULL,
    name varchar(256) NOT NULL,
    email varchar(256),
    img_id int REFERENCES images DEFAULT NULL,
    pub boolean NOT NULL DEFAULT true,
    admin boolean NOT NULL DEFAULT false,
    UNIQUE (oauth_id, src)
);

CREATE TABLE IF NOT EXISTS climbs (
    climber integer NOT NULL,
    summit integer NOT NULL,
    ts date,
    comment text,
    PRIMARY KEY (climber, summit)
);
