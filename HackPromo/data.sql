--====================================================
drop table if exists tt_offers;

create temp table tt_offers as
select distinct
    "Offer_ID",
    start_date,
    start_date - interval '6 months' as start_date_6m,
    end_date,
    (end_date::date - start_date::date)::int as num_days,
    "Promo_type"
from
    offers;

create unique index ui_tt_offers_offer_id on tt_offers("Offer_ID");
create index i_tt_offers_start_date on tt_offers(start_date, start_date_6m);
--====================================================
drop table if exists tt_offer_checks;

create temp table tt_offer_checks as
with _checks as (
    select distinct
        check_id,
        day
    from
        checks
)
select
    O."Offer_ID",
    count(C.check_id) as num_checks
from
    tt_offers as O
    -----
    inner join _checks as C on
        C.day < O.start_date
        and C.day >= O.start_date_6m
group by
    O."Offer_ID";

create unique index ui_tt_offer_checks_offer_id on tt_offer_checks("Offer_ID");
--====================================================
drop table if exists tt_offer_sku_checks;

create temp table tt_offer_sku_checks as
select
    O."Offer_ID",
    O.sku,
    count(distinct C.check_id) as num_checks,
    avg(C.num_sales) as avg_num_sales,
    avg((C.selling_price - C.supplier_price) / C.num_sales) as avg_margin,
    avg(C.selling_price / C.num_sales) as avg_price,
    stddev(C.selling_price / C.num_sales) as std_price
from
    offers as O
    -----
    inner join tt_offers as UO on
        O."Offer_ID" = UO."Offer_ID"
    -----
    inner join checks as C on
        O.sku = C.sku
        and C.day < UO.start_date
        and C.day >= UO.start_date_6m
group by
    O."Offer_ID",
    O.sku;

create index i_tt_offer_sku_checks_offer_id on tt_offer_sku_checks("Offer_ID");
--====================================================
create temp table tt_offer_calendar as
select
    O."Offer_ID",
    count(case when C.date_type = 'праздничный' then 1 end) as holidays,
    count(case when C.date_type = 'предпраздничный' then 1 end) as pre_holidays,
    count(case when C.date_type = 'выходной' then 1 end) as weekends,
    count(case when C.date_type = 'рабочий' then 1 end) as workings
from
    tt_offers as O
    -----
    left join calendar as C on
        C.date between O.start_date and O.end_date
group by
    O."Offer_ID";

create index i_tt_offer_calendar_offer_id on tt_offer_calendar("Offer_ID");
--====================================================
drop table if exists datamart.offer_features1;

create table datamart.offer_features1 as
select
    UO."Offer_ID",
    UO.num_days,
    UO."Promo_type",
    OCA.holidays,
    OCA.pre_holidays,
    OCA.weekends,
    OCA.workings,
    avg(OSC.num_checks * 1.0 / OC.num_checks) as sku_checks_share,
    avg(OSC.avg_num_sales) as avg_num_sales,
    avg(OSC.avg_margin) as avg_margin,
    avg(OSC.avg_price) as avg_price,
    avg(OSC.std_price) as std_price
from
    tt_offers as UO
    -----
    left join tt_offer_checks as OC on
        UO."Offer_ID" = OC."Offer_ID"
    -----
    left join tt_offer_sku_checks as OSC on
        UO."Offer_ID" = OSC."Offer_ID"
    -----
    left join tt_offer_calendar as OCA on
        UO."Offer_ID" = OCA."Offer_ID"
group by
    UO."Offer_ID",
    UO.num_days,
    UO."Promo_type",
    OCA.holidays,
    OCA.pre_holidays,
    OCA.weekends,
    OCA.workings;

create unique index ui_offer_features1_offer_id on datamart.offer_features1("Offer_ID");
