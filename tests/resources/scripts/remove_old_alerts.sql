# USED TO SCRUB A PRODUCTION DB DOWN TO A FEW DAYS OF DATA

delete from hierarchy where hierarchy.parent in (
	select id from alerts where push_date<str_to_date('20140901', '%Y%m%d')
);
delete from hierarchy where hierarchy.child in (
	select id from alerts where push_date<str_to_date('20140901', '%Y%m%d')
);

delete from alerts where push_date<str_to_date('20140901', '%Y%m%d');
commit;
