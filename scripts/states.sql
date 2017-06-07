--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: res_country_state; Type: TABLE; Schema: public; Owner: openerp; Tablespace: 
--

CREATE TABLE res_country_state (
    id integer NOT NULL,
    create_uid integer,
    create_date timestamp without time zone,
    write_date timestamp without time zone,
    write_uid integer,
    code character varying(3) NOT NULL,
    country_id integer NOT NULL,
    name character varying(64) NOT NULL
);


ALTER TABLE public.res_country_state OWNER TO openerp;

--
-- Name: TABLE res_country_state; Type: COMMENT; Schema: public; Owner: openerp
--

COMMENT ON TABLE res_country_state IS 'Country state';


--
-- Name: COLUMN res_country_state.code; Type: COMMENT; Schema: public; Owner: openerp
--

COMMENT ON COLUMN res_country_state.code IS 'State Code';


--
-- Name: COLUMN res_country_state.country_id; Type: COMMENT; Schema: public; Owner: openerp
--

COMMENT ON COLUMN res_country_state.country_id IS 'Country';


--
-- Name: COLUMN res_country_state.name; Type: COMMENT; Schema: public; Owner: openerp
--

COMMENT ON COLUMN res_country_state.name IS 'State Name';


--
-- Name: res_country_state_id_seq; Type: SEQUENCE; Schema: public; Owner: openerp
--

CREATE SEQUENCE res_country_state_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.res_country_state_id_seq OWNER TO openerp;

--
-- Name: res_country_state_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: openerp
--

ALTER SEQUENCE res_country_state_id_seq OWNED BY res_country_state.id;


--
-- Name: res_country_state_id_seq; Type: SEQUENCE SET; Schema: public; Owner: openerp
--

SELECT pg_catalog.setval('res_country_state_id_seq', 67, true);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: openerp
--

ALTER TABLE ONLY res_country_state ALTER COLUMN id SET DEFAULT nextval('res_country_state_id_seq'::regclass);


--
-- Data for Name: res_country_state; Type: TABLE DATA; Schema: public; Owner: openerp
--

COPY res_country_state (id, create_uid, create_date, write_date, write_uid, code, country_id, name) FROM stdin;
1	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	AL	235	Alabama
2	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	AK	235	Alaska
3	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	AZ	235	Arizona
4	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	AR	235	Arkansas
5	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	CA	235	California
6	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	CO	235	Colorado
7	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	CT	235	Connecticut
8	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	DE	235	Delaware
9	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	DC	235	District of Columbia
10	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	FL	235	Florida
11	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	GA	235	Georgia
12	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	HI	235	Hawaii
13	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	ID	235	Idaho
14	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	IL	235	Illinois
15	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	IN	235	Indiana
16	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	IA	235	Iowa
17	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	KS	235	Kansas
18	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	KY	235	Kentucky
19	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	LA	235	Louisiana
20	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	ME	235	Maine
21	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	MT	235	Montana
22	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	NE	235	Nebraska
23	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	NV	235	Nevada
24	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	NH	235	New Hampshire
25	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	NJ	235	New Jersey
26	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	NM	235	New Mexico
27	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	NY	235	New York
28	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	NC	235	North Carolina
29	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	ND	235	North Dakota
30	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	OH	235	Ohio
31	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	OK	235	Oklahoma
32	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	OR	235	Oregon
33	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	MD	235	Maryland
34	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	MA	235	Massachusetts
35	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	MI	235	Michigan
36	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	MN	235	Minnesota
37	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	MS	235	Mississippi
38	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	MO	235	Missouri
39	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	PA	235	Pennsylvania
40	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	RI	235	Rhode Island
41	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	SC	235	South Carolina
42	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	SD	235	South Dakota
43	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	TN	235	Tennessee
44	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	TX	235	Texas
45	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	UT	235	Utah
46	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	VT	235	Vermont
47	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	VA	235	Virginia
48	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	WA	235	Washington
49	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	WV	235	West Virginia
50	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	WI	235	Wisconsin
51	1	2013-02-18 18:23:26.636178	2013-02-18 18:23:26.636178	1	WY	235	Wyoming
53	1	2013-03-01 18:56:40.740688	2013-03-01 18:56:40.740688	1	AB	39	Alberta
55	1	2013-03-01 18:57:19.286242	2013-03-01 18:57:19.286242	1	BC	39	British Columbia
56	1	2013-03-01 18:57:42.573171	2013-03-01 18:57:42.573171	1	MB	39	Manitoba
57	1	2013-03-01 18:59:56.403786	2013-03-01 18:59:56.403786	1	NB	39	New Brunswick
58	1	2013-03-01 19:06:22.184847	2013-03-01 19:06:22.184847	1	NL	39	Newfoundland and Labrador
60	1	2013-03-01 19:07:20.720575	2013-03-01 19:07:20.720575	1	ON	39	Ontario
61	1	2013-03-01 19:08:49.817208	2013-03-01 19:08:49.817208	1	PE	39	Prince Edward Island
62	1	2013-03-01 19:09:11.381403	2013-03-01 19:09:11.381403	1	QC	39	Quebec
63	1	2013-03-01 19:09:33.615523	2013-03-01 19:09:33.615523	1	SK	39	Saskatchewan
64	1	2013-03-01 19:10:10.68971	2013-03-01 19:10:10.68971	1	NT	39	Northwest Territories
65	1	2013-03-01 19:10:54.987767	2013-03-01 19:10:54.987767	1	YT	39	Yukon
66	1	2013-03-01 19:11:12.914568	2013-03-01 19:11:12.914568	1	NU	39	Nunavut
67	1	2013-03-06 21:53:46.46387	2013-03-06 21:53:46.46387	1	PR	235	Puerto Rico
59	1	2013-03-01 19:06:55.086548	2013-03-01 19:06:55.086548	1	NS	39	Nova Scotia
68	1	2017-06-07 09:51:00.000000	2017-06-07 09:51:00.000000	1	AS	235	American Samoa
\.


--
-- Name: res_country_state_pkey; Type: CONSTRAINT; Schema: public; Owner: openerp; Tablespace: 
--

ALTER TABLE ONLY res_country_state
    ADD CONSTRAINT res_country_state_pkey PRIMARY KEY (id);


--
-- Name: res_country_state_country_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: openerp
--

ALTER TABLE ONLY res_country_state
    ADD CONSTRAINT res_country_state_country_id_fkey FOREIGN KEY (country_id) REFERENCES res_country(id) ON DELETE SET NULL;


--
-- Name: res_country_state_create_uid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: openerp
--

ALTER TABLE ONLY res_country_state
    ADD CONSTRAINT res_country_state_create_uid_fkey FOREIGN KEY (create_uid) REFERENCES res_users(id) ON DELETE SET NULL;


--
-- Name: res_country_state_write_uid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: openerp
--

ALTER TABLE ONLY res_country_state
    ADD CONSTRAINT res_country_state_write_uid_fkey FOREIGN KEY (write_uid) REFERENCES res_users(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

