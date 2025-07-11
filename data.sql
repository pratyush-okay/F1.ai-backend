--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.5 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: current_drivers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.current_drivers (driver_id, name, surname, nationality, birthday, number, short_name, url, team_id, created_at, updated_at) FROM stdin;
piastri	Oscar	Piastri	Australia	06/04/2001	81	PIA	https://en.wikipedia.org/wiki/Oscar_Piastri	mclaren	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828365+00
norris	Lando	Norris	Great Britain	13/11/1999	4	NOR	https://en.wikipedia.org/wiki/Lando_Norris	mclaren	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828376+00
max_verstappen	Max	Verstappen	Netherlands	30/09/1997	33	VER	https://en.wikipedia.org/wiki/Max_Verstappen	red_bull	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.82838+00
russell	George	Russell	Great Britain	15/02/1998	63	RUS	https://en.wikipedia.org/wiki/George_Russell_(racing_driver)	mercedes	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828384+00
leclerc	Charles	Leclerc	Monaco	16/10/1997	16	LEC	https://en.wikipedia.org/wiki/Charles_Leclerc	ferrari	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828387+00
hamilton	Lewis	Hamilton	Great Britain	07/01/1985	44	HAM	https://en.wikipedia.org/wiki/Lewis_Hamilton	ferrari	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.82839+00
antonelli	Andrea	Kimi Antonelli	Italian	2006-08-25	12	ANT	https://en.wikipedia.org/wiki/Andrea_Kimi_Antonelli	mercedes	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828393+00
albon	Alex	Albon	Thailand	23/03/1996	23	ALB	https://en.wikipedia.org/wiki/Alex_Albon	williams	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828401+00
ocon	Esteban	Ocon	France	17/09/1996	31	OCO	https://en.wikipedia.org/wiki/Esteban_Ocon	haas	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828405+00
hulkenberg	Nico	Hulkenberg	Germany	19/08/1987	27	HUL	https://en.wikipedia.org/wiki/Nico_H%C3%BClkenberg	sauber	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828408+00
hadjar	Isack	Hadjar	France	28/02/2004	6	HAD	https://en.wikipedia.org/wiki/Isack_Hadjar	rb	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828411+00
stroll	Lance	Stroll	Canada	29/10/1998	18	STR	https://en.wikipedia.org/wiki/Lance_Stroll	aston_martin	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828415+00
alonso	Fernando	Alonso	Spain	29/07/1981	14	ALO	https://en.wikipedia.org/wiki/Fernando_Alonso	aston_martin	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828418+00
sainz	Carlos	Sainz	Spain	01/09/1994	55	SAI	https://en.wikipedia.org/wiki/Carlos_Sainz_Jr.	williams	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.82842+00
lawson	Liam	Lawson	New Zealander	2002-02-11	30	LAW	http://en.wikipedia.org/wiki/Liam_Lawson	rb	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828423+00
gasly	Pierre	Gasly	France	07/02/1996	10	GAS	https://en.wikipedia.org/wiki/Pierre_Gasly	alpine	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828425+00
tsunoda	Yuki	Tsunoda	Japan	11/05/2000	22	TSU	https://en.wikipedia.org/wiki/Yuki_Tsunoda	red_bull	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828427+00
bearman	Oliver	Bearman	Great Britain	08/05/2005	87	BEA	https://en.wikipedia.org/wiki/Oliver_Bearman	haas	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.82843+00
bortoleto	Gabriel	Bortoleto	Brazil	2004-10-14	5	BOR	https://en.wikipedia.org/wiki/Gabriel_Bortoleto	sauber	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828432+00
colapinto	Franco	Colapinto	Argentine	27/05/2003	43	COL	https://en.wikipedia.org/wiki/Franco_Colapinto	alpine	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828435+00
doohan	Jack	Doohan	Australia	20/01/2003	7	DOO	https://en.wikipedia.org/wiki/Jack_Doohan_(racing_driver)	alpine	2025-07-02 10:17:19.785849+00	2025-07-02 10:17:18.828437+00
\.


--
-- Data for Name: current_teams; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.current_teams (team_id, team_name, team_nationality, first_appearance, constructors_championships, drivers_championships, url, created_at, updated_at) FROM stdin;
mclaren	McLaren Formula 1 Team	Great Britain	1966	9	12	https://en.wikipedia.org/wiki/McLaren	2025-07-02 10:28:47.234018+00	2025-07-02 10:28:46.303563+00
ferrari	Scuderia Ferrari	Italy	1950	16	15	https://en.wikipedia.org/wiki/Scuderia_Ferrari	2025-07-02 10:28:47.234018+00	2025-07-02 10:28:46.303588+00
mercedes	Mercedes Formula 1 Team	Germany	1954	8	9	https://en.wikipedia.org/wiki/Mercedes-Benz_in_Formula_One	2025-07-02 10:28:47.234018+00	2025-07-02 10:28:46.303594+00
red_bull	Red Bull Racing	Austria	2005	6	8	https://en.wikipedia.org/wiki/Red_Bull_Racing	2025-07-02 10:28:47.234018+00	2025-07-02 10:28:46.303599+00
williams	Williams Racing	Great Britain	1977	9	7	https://en.wikipedia.org/wiki/Williams_Grand_Prix_Engineering	2025-07-02 10:28:47.234018+00	2025-07-02 10:28:46.303605+00
rb	RB F1 Team	Italy	2024	\N	\N	https://en.wikipedia.org/wiki/RB_Formula_One_Team	2025-07-02 10:28:47.234018+00	2025-07-02 10:28:46.30361+00
haas	Haas F1 Team	United States	2016	\N	\N	https://en.wikipedia.org/wiki/Haas_F1_Team	2025-07-02 10:28:47.234018+00	2025-07-02 10:28:46.303615+00
aston_martin	Aston Martin F1 Team	Great Britain	1959	\N	\N	https://en.wikipedia.org/wiki/Aston_Martin_in_Formula_One	2025-07-02 10:28:47.234018+00	2025-07-02 10:28:46.303623+00
sauber	Sauber F1 Team	Switzerland	1993	\N	\N	https://en.wikipedia.org/wiki/Sauber_Motorsport	2025-07-02 10:28:47.234018+00	2025-07-02 10:28:46.303627+00
alpine	Alpine F1 Team	France	2021	\N	\N	https://en.wikipedia.org/wiki/Alpine_F1_Team	2025-07-02 10:28:47.234018+00	2025-07-02 10:28:46.303631+00
\.


--
-- Data for Name: current_drivers_standings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.current_drivers_standings (classification_id, driver_id, team_id, season, championship_id, points, "position", wins, created_at, updated_at) FROM stdin;
3399	piastri	mclaren	2025	f1_2025	216	1	5	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291113+00
3403	norris	mclaren	2025	f1_2025	201	2	3	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291123+00
3392	max_verstappen	red_bull	2025	f1_2025	155	3	2	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291125+00
3404	russell	mercedes	2025	f1_2025	146	4	1	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291126+00
3410	leclerc	ferrari	2025	f1_2025	119	5	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291127+00
3401	hamilton	ferrari	2025	f1_2025	91	6	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291129+00
3409	antonelli	mercedes	2025	f1_2025	63	7	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.29113+00
3396	albon	williams	2025	f1_2025	42	8	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291134+00
3393	ocon	haas	2025	f1_2025	23	9	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291136+00
3405	hulkenberg	sauber	2025	f1_2025	22	10	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291137+00
3402	hadjar	rb	2025	f1_2025	21	11	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291138+00
3398	stroll	aston_martin	2025	f1_2025	14	12	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291139+00
3400	alonso	aston_martin	2025	f1_2025	14	13	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.29114+00
3406	sainz	williams	2025	f1_2025	13	14	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291142+00
3394	lawson	rb	2025	f1_2025	12	15	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291143+00
3395	gasly	alpine	2025	f1_2025	11	16	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291144+00
3397	tsunoda	red_bull	2025	f1_2025	10	17	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291145+00
3407	bearman	haas	2025	f1_2025	6	18	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291146+00
3411	bortoleto	sauber	2025	f1_2025	4	19	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291147+00
3413	colapinto	alpine	2025	f1_2025	0	20	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291148+00
3408	doohan	alpine	2025	f1_2025	0	21	\N	2025-07-02 10:43:10.262348+00	2025-07-02 10:43:09.291149+00
\.


--
-- Data for Name: current_teams_standings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.current_teams_standings (classification_id, team_id, season, championship_id, points, "position", wins, created_at, updated_at) FROM stdin;
930	mclaren	2025	f1_2025	417	1	8	2025-07-02 10:56:11.536538+00	2025-07-02 10:56:10.586588+00
927	ferrari	2025	f1_2025	210	2	\N	2025-07-02 10:56:11.536538+00	2025-07-02 10:56:10.586595+00
922	mercedes	2025	f1_2025	209	3	1	2025-07-02 10:56:11.536538+00	2025-07-02 10:56:10.586597+00
921	red_bull	2025	f1_2025	162	4	2	2025-07-02 10:56:11.536538+00	2025-07-02 10:56:10.586598+00
926	williams	2025	f1_2025	55	5	\N	2025-07-02 10:56:11.536538+00	2025-07-02 10:56:10.5866+00
929	rb	2025	f1_2025	36	6	\N	2025-07-02 10:56:11.536538+00	2025-07-02 10:56:10.586601+00
925	haas	2025	f1_2025	29	7	\N	2025-07-02 10:56:11.536538+00	2025-07-02 10:56:10.586603+00
924	aston_martin	2025	f1_2025	28	8	\N	2025-07-02 10:56:11.536538+00	2025-07-02 10:56:10.586606+00
928	sauber	2025	f1_2025	26	9	\N	2025-07-02 10:56:11.536538+00	2025-07-02 10:56:10.586608+00
923	alpine	2025	f1_2025	11	10	\N	2025-07-02 10:56:11.536538+00	2025-07-02 10:56:10.586609+00
\.


--
-- PostgreSQL database dump complete
--

