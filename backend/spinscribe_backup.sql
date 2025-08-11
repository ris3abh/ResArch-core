--
-- PostgreSQL database dump
--

-- Dumped from database version 15.13 (Debian 15.13-1.pgdg120+1)
-- Dumped by pg_dump version 15.13 (Debian 15.13-1.pgdg120+1)

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
-- Name: chat_instances; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_instances (
    project_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    chat_type character varying(50),
    is_active boolean NOT NULL,
    created_by uuid NOT NULL,
    agent_config jsonb,
    workflow_id character varying(100),
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.chat_instances OWNER TO postgres;

--
-- Name: chat_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages (
    chat_instance_id uuid NOT NULL,
    sender_id uuid,
    sender_type character varying(50) NOT NULL,
    agent_type character varying(100),
    message_content text NOT NULL,
    message_type character varying(50),
    message_metadata jsonb,
    parent_message_id uuid,
    is_edited boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.chat_messages OWNER TO postgres;

--
-- Name: documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.documents (
    filename character varying(255) NOT NULL,
    original_filename character varying(255) NOT NULL,
    file_size integer NOT NULL,
    file_type character varying(100) NOT NULL,
    file_path character varying(500) NOT NULL,
    project_id uuid NOT NULL,
    uploaded_by_id uuid NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.documents OWNER TO postgres;

--
-- Name: projects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.projects (
    name character varying(200) NOT NULL,
    description text,
    client_name character varying(200),
    owner_id uuid NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.projects OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    first_name character varying(100) NOT NULL,
    last_name character varying(100) NOT NULL,
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Data for Name: chat_instances; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chat_instances (project_id, name, description, chat_type, is_active, created_by, agent_config, workflow_id, id, created_at, updated_at) FROM stdin;
503a31ab-538d-4b05-b9a5-76b27e6aaaa9	Yanmar - Local Article	string	standard	t	6d9304dd-741a-41bc-9f19-533fc23714ef	{}	\N	5d32adbc-cef5-44e4-8c87-00d470e3e5e2	2025-07-28 21:00:35.937252	2025-07-28 21:00:35.937258
\.


--
-- Data for Name: chat_messages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chat_messages (chat_instance_id, sender_id, sender_type, agent_type, message_content, message_type, message_metadata, parent_message_id, is_edited, id, created_at, updated_at) FROM stdin;
5d32adbc-cef5-44e4-8c87-00d470e3e5e2	6d9304dd-741a-41bc-9f19-533fc23714ef	user	\N	Hi! I need help creating an article about sustainable farming technology for Yanmar.	text	{}	\N	f	68cd5d55-9608-404b-a9cf-cd2273fae7e4	2025-07-29 16:05:52.478683	2025-07-29 16:05:52.478686
5d32adbc-cef5-44e4-8c87-00d470e3e5e2	6d9304dd-741a-41bc-9f19-533fc23714ef	user	\N	Hi! I need help creating an article about sustainable farming technology for Yanmar.	text	{}	\N	f	be177b12-4c68-455e-9cd7-dce1fffa78a5	2025-07-29 16:09:55.691645	2025-07-29 16:09:55.691647
5d32adbc-cef5-44e4-8c87-00d470e3e5e2	\N	agent	coordinator	🚀 Starting SpinScribe workflow to create: Create an article about sustainable farming technology trends	system	{"workflow_status": "starting", "task_description": "Create an article about sustainable farming technology trends"}	\N	f	20abfddb-a0a2-49e9-9c5c-4573485fcd3c	2025-07-29 16:10:48.932912	2025-07-29 16:10:48.932914
5d32adbc-cef5-44e4-8c87-00d470e3e5e2	\N	agent	style_analysis	🔍 Analyzing your brand voice and style preferences...	text	{"agent_status": "working", "workflow_stage": "style_analysis"}	\N	f	153de6bc-7216-49c5-9944-658e7a7c288c	2025-07-29 16:10:48.936486	2025-07-29 16:10:48.936488
5d32adbc-cef5-44e4-8c87-00d470e3e5e2	\N	agent	coordinator	🚀 Starting SpinScribe workflow to create: Create an article about sustainable farming technology trends	system	{"workflow_status": "starting", "task_description": "Create an article about sustainable farming technology trends"}	\N	f	f81953a5-9ca0-46d0-9c0f-6c75e7d16a25	2025-07-29 16:13:16.044499	2025-07-29 16:13:16.044501
5d32adbc-cef5-44e4-8c87-00d470e3e5e2	\N	agent	style_analysis	🔍 Analyzing your brand voice and style preferences...	text	{"agent_status": "working", "workflow_stage": "style_analysis"}	\N	f	5933f2c7-d2fe-44f9-9a8b-0e6e2cb5bd20	2025-07-29 16:13:16.047785	2025-07-29 16:13:16.047787
5d32adbc-cef5-44e4-8c87-00d470e3e5e2	6d9304dd-741a-41bc-9f19-533fc23714ef	user	\N	Please focus on precision agriculture and smart farming solutions in the article.	text	{"topic_focus": "precision_agriculture"}	\N	f	636a433a-298b-448a-9aab-d7544a441f58	2025-07-29 16:13:43.748165	2025-07-29 16:13:43.748167
5d32adbc-cef5-44e4-8c87-00d470e3e5e2	\N	agent	coordinator	🚀 Starting SpinScribe workflow to create: Create a detailed article about precision agriculture innovations	system	{"workflow_status": "starting", "task_description": "Create a detailed article about precision agriculture innovations"}	\N	f	ed4e2fa9-dee3-4077-b18f-efd634d94755	2025-07-31 15:23:06.851307	2025-07-31 15:23:06.851311
5d32adbc-cef5-44e4-8c87-00d470e3e5e2	\N	agent	style_analysis	🔍 Analyzing your brand voice and style preferences...	text	{"agent_status": "working", "workflow_stage": "style_analysis"}	\N	f	1df38ed9-090b-41e7-b993-6bce52fa91a7	2025-07-31 15:23:06.855861	2025-07-31 15:23:06.855863
\.


--
-- Data for Name: documents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.documents (filename, original_filename, file_size, file_type, file_path, project_id, uploaded_by_id, id, created_at, updated_at) FROM stdin;
decbac76-d45a-4f61-82d5-1b4420de5979.pdf	Blogs, Locals, Landing Page Templates and Outlines .pdf	212450	application/pdf	storage/uploads/9b26e847-5d5a-4967-8a76-75566d1de4c7/decbac76-d45a-4f61-82d5-1b4420de5979.pdf	9b26e847-5d5a-4967-8a76-75566d1de4c7	857999b3-34f5-4d93-be40-bd92344ee33c	052ca879-0b59-4211-9974-a737bc5dd2d5	2025-07-23 18:26:02.244385	2025-07-23 18:26:02.244397
2234adea-789d-4bb5-986e-2d992f3d8531.pdf	Content Style Guide - Techflow Solutions.pdf	196441	application/pdf	storage/uploads/9b26e847-5d5a-4967-8a76-75566d1de4c7/2234adea-789d-4bb5-986e-2d992f3d8531.pdf	9b26e847-5d5a-4967-8a76-75566d1de4c7	857999b3-34f5-4d93-be40-bd92344ee33c	70aa7535-79ad-4041-a2d9-086d6044d847	2025-07-23 18:26:41.493933	2025-07-23 18:26:41.493943
67d14396-daba-4472-a2b8-3cf460b948ed.pdf	Brand Guide - Techflow Solutions.pdf	228645	application/pdf	storage/uploads/503a31ab-538d-4b05-b9a5-76b27e6aaaa9/67d14396-daba-4472-a2b8-3cf460b948ed.pdf	503a31ab-538d-4b05-b9a5-76b27e6aaaa9	6d9304dd-741a-41bc-9f19-533fc23714ef	5a5a601a-964f-4cfa-bbe9-17803666eac4	2025-07-25 19:18:41.315623	2025-07-25 19:18:41.315633
68dedbc0-0cc8-471c-8fcb-82ddfc7efd9d.md	agents.md	7337	application/octet-stream	storage/uploads/503a31ab-538d-4b05-b9a5-76b27e6aaaa9/68dedbc0-0cc8-471c-8fcb-82ddfc7efd9d.md	503a31ab-538d-4b05-b9a5-76b27e6aaaa9	6d9304dd-741a-41bc-9f19-533fc23714ef	316ec684-b6e3-4f11-9e4e-d5531da7d4e0	2025-07-25 19:22:35.25704	2025-07-25 19:22:35.257046
d1648419-baee-4122-b45f-88eb53f2482e.pdf	Blogs, Locals, Landing Page Templates and Outlines .pdf	212450	application/pdf	storage/uploads/503a31ab-538d-4b05-b9a5-76b27e6aaaa9/d1648419-baee-4122-b45f-88eb53f2482e.pdf	503a31ab-538d-4b05-b9a5-76b27e6aaaa9	6d9304dd-741a-41bc-9f19-533fc23714ef	a5c8b9fc-6a18-4ec4-94f9-b650254f026b	2025-07-28 13:57:26.476986	2025-07-28 13:57:26.476994
1f8a6c44-39f3-44ee-9e35-b1f4173b3dfd.pdf	Brand Guide - Techflow Solutions.pdf	228645	application/pdf	storage/uploads/503a31ab-538d-4b05-b9a5-76b27e6aaaa9/1f8a6c44-39f3-44ee-9e35-b1f4173b3dfd.pdf	503a31ab-538d-4b05-b9a5-76b27e6aaaa9	6d9304dd-741a-41bc-9f19-533fc23714ef	85d3a5ab-9192-4163-9ac8-546908272c4c	2025-07-28 14:40:42.01425	2025-07-28 14:40:42.014258
2570e080-36ce-4029-98c5-0ddd4ccc202f.pdf	19782_Chain_of_Agents_Large_La (1).pdf	2683436	application/pdf	storage/uploads/503a31ab-538d-4b05-b9a5-76b27e6aaaa9/2570e080-36ce-4029-98c5-0ddd4ccc202f.pdf	503a31ab-538d-4b05-b9a5-76b27e6aaaa9	6d9304dd-741a-41bc-9f19-533fc23714ef	a09ddcc3-5248-46c4-90f5-740989caf76b	2025-07-28 20:58:13.117387	2025-07-28 20:58:13.117396
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.projects (name, description, client_name, owner_id, id, created_at, updated_at) FROM stdin;
Spinutech	string	string	857999b3-34f5-4d93-be40-bd92344ee33c	9b26e847-5d5a-4967-8a76-75566d1de4c7	2025-07-23 18:25:23.14216	2025-07-23 18:25:23.142164
Spinutech - Chatbot	We gotta work on some content for the client	Yanmar	6d9304dd-741a-41bc-9f19-533fc23714ef	503a31ab-538d-4b05-b9a5-76b27e6aaaa9	2025-07-25 18:53:41.617279	2025-07-25 18:53:41.617286
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (email, hashed_password, first_name, last_name, is_active, id, created_at, updated_at) FROM stdin;
test@spinscribe.com	$2b$12$ugYyR6qzH6MyU3P/zTDoJu0RMrB.NdDQT1zn/F4kV/KfbgT5yyJwy	Test	User	t	857999b3-34f5-4d93-be40-bd92344ee33c	2025-07-23 15:49:45.044632	2025-07-23 15:49:45.044636
rishabh.sharma@spinutech.com	$2b$12$a/eGkeYx4d5Fsf5n7VAc8O.F82l7qOjiXViJdFDVxmlkttXknoW9K	Rishabh	Sharma	t	6d9304dd-741a-41bc-9f19-533fc23714ef	2025-07-25 18:52:59.193769	2025-07-25 18:52:59.193773
sarah.butler@spinutech.com	$2b$12$hSyyjG6MPNlETk.SrNlqP.Ku/ZBuzhBW1f7f9alc8ImHy/9LphRUO	Sarah	Butler	t	71256f2b-0d55-4e0c-8841-9c28ae108dc3	2025-07-25 19:02:31.928222	2025-07-25 19:02:31.928228
\.


--
-- Name: chat_instances chat_instances_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_instances
    ADD CONSTRAINT chat_instances_pkey PRIMARY KEY (id);


--
-- Name: chat_messages chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: chat_instances chat_instances_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_instances
    ADD CONSTRAINT chat_instances_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: chat_instances chat_instances_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_instances
    ADD CONSTRAINT chat_instances_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: chat_messages chat_messages_chat_instance_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_chat_instance_id_fkey FOREIGN KEY (chat_instance_id) REFERENCES public.chat_instances(id) ON DELETE CASCADE;


--
-- Name: chat_messages chat_messages_parent_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_parent_message_id_fkey FOREIGN KEY (parent_message_id) REFERENCES public.chat_messages(id);


--
-- Name: chat_messages chat_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id);


--
-- Name: documents documents_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: documents documents_uploaded_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_uploaded_by_id_fkey FOREIGN KEY (uploaded_by_id) REFERENCES public.users(id);


--
-- Name: projects projects_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

