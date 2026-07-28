--
-- PostgreSQL database dump
--


-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: consumer; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.consumer (
    sessionid integer NOT NULL,
    date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: consumer_sessionid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.consumer_sessionid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: consumer_sessionid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.consumer_sessionid_seq OWNED BY public.consumer.sessionid;


--
-- Name: diagnostic_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.diagnostic_log (
    logid integer NOT NULL,
    condition_detected character varying(50) NOT NULL,
    confidence_score double precision,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    referral_flag boolean
);



--
-- Name: diagnostic_log_logid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.diagnostic_log_logid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: diagnostic_log_logid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.diagnostic_log_logid_seq OWNED BY public.diagnostic_log.logid;


--
-- Name: ingredient_db; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ingredient_db (
    ingredientid integer NOT NULL,
    active_compound character varying(255) NOT NULL,
    treatment_phase character varying(255) NOT NULL,
    dermatological_logic text,
    target_condition character varying(50)
);



--
-- Name: ingredient_db_ingredientid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ingredient_db_ingredientid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: ingredient_db_ingredientid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ingredient_db_ingredientid_seq OWNED BY public.ingredient_db.ingredientid;


--
-- Name: treatment_mapping; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.treatment_mapping (
    mapid integer NOT NULL,
    condition_label character varying(50) NOT NULL,
    ingredientid integer
);



--
-- Name: treatment_mapping_mapid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.treatment_mapping_mapid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: treatment_mapping_mapid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.treatment_mapping_mapid_seq OWNED BY public.treatment_mapping.mapid;


--
-- Name: consumer sessionid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.consumer ALTER COLUMN sessionid SET DEFAULT nextval('public.consumer_sessionid_seq'::regclass);


--
-- Name: diagnostic_log logid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.diagnostic_log ALTER COLUMN logid SET DEFAULT nextval('public.diagnostic_log_logid_seq'::regclass);


--
-- Name: ingredient_db ingredientid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ingredient_db ALTER COLUMN ingredientid SET DEFAULT nextval('public.ingredient_db_ingredientid_seq'::regclass);


--
-- Name: treatment_mapping mapid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.treatment_mapping ALTER COLUMN mapid SET DEFAULT nextval('public.treatment_mapping_mapid_seq'::regclass);


--
-- Name: consumer consumer_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.consumer
    ADD CONSTRAINT consumer_pkey PRIMARY KEY (sessionid);


--
-- Name: diagnostic_log diagnostic_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.diagnostic_log
    ADD CONSTRAINT diagnostic_log_pkey PRIMARY KEY (logid);


--
-- Name: ingredient_db ingredient_db_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ingredient_db
    ADD CONSTRAINT ingredient_db_pkey PRIMARY KEY (ingredientid);


--
-- Name: treatment_mapping treatment_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.treatment_mapping
    ADD CONSTRAINT treatment_mapping_pkey PRIMARY KEY (mapid);


--
-- Name: idx_ingredient_condition; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ingredient_condition ON public.ingredient_db USING btree (target_condition);


--
-- Name: idx_log_condition; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_log_condition ON public.diagnostic_log USING btree (condition_detected);


--
-- Name: idx_log_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_log_timestamp ON public.diagnostic_log USING btree (created_at);


--
-- Name: idx_mapping_condition; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mapping_condition ON public.treatment_mapping USING btree (condition_label);


--
-- Name: treatment_mapping treatment_mapping_ingredientid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.treatment_mapping
    ADD CONSTRAINT treatment_mapping_ingredientid_fkey FOREIGN KEY (ingredientid) REFERENCES public.ingredient_db(ingredientid) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--


