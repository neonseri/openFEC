import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

from webservices.rest import db
from webservices.partition.base import TableGroup

class SchedBGroup(TableGroup):

    parent = 'fec_fitem_sched_b_vw'
    base_name = 'ofec_sched_b'
    queue_new = 'ofec_sched_b_queue_new'
    queue_old = 'ofec_sched_b_queue_old'
    primary = 'sub_id'
    transaction_date_column = 'disb_dt'

    columns = [
        sa.Column('timestamp', sa.DateTime),
        sa.Column('pg_date', sa.DateTime),
        sa.Column('pdf_url', sa.Text),
        sa.Column('recipient_name_text', TSVECTOR),
        sa.Column('disbursement_description_text', TSVECTOR),
        sa.Column('disbursement_purpose_category', sa.String),
        sa.Column('clean_recipient_cmte_id', sa.String),
        sa.Column('two_year_transaction_period', sa.SmallInteger),
        sa.Column('line_number_label', sa.Text),
    ]

    column_mappings = {
        'schedule_type': sa.VARCHAR(length=2)
    }

    @classmethod
    def column_factory(cls, parent):
        return [
            sa.cast(sa.func.current_timestamp(), sa.DateTime).label('pg_date'),
            sa.func.image_pdf_url(parent.c.image_num).label('pdf_url'),
            sa.func.to_tsvector(
                sa.func.concat(parent.c.recipient_nm, ' ', parent.c.recipient_cmte_id),
            ).label('recipient_name_text'),
            sa.func.to_tsvector(parent.c.disb_desc).label('disbursement_description_text'),
            sa.func.disbursement_purpose(
                parent.c.disb_tp,
                parent.c.disb_desc,
            ).label('disbursement_purpose_category'),
            sa.func.clean_repeated(
                parent.c.recipient_cmte_id,
                parent.c.cmte_id,
            ).label('clean_recipient_cmte_id'),
            sa.func.cast(
                sa.func.get_cycle(parent.c.rpt_yr), sa.SmallInteger
            ).label('two_year_transaction_period'),
            sa.func.expand_line_number(
                parent.c.filing_form,
                parent.c.line_num,
            ).label('line_number_label'),
        ]

    @classmethod
    def index_factory(cls, child):
        c = child.c
        return [
            sa.Index(None, c.rpt_yr),
            sa.Index(None, c.pg_date),
            sa.Index(None, c.image_num),
            sa.Index(None, c.recipient_st),
            sa.Index(None, c.recipient_city),
            sa.Index(None, c.clean_recipient_cmte_id),
            sa.Index(None, c.two_year_transaction_period),
            sa.Index(None, c.line_num, child.c[cls.primary]),

            sa.Index('ix_{0}_sub_id_date_tmp'.format(child.name[:-4]), c.disb_dt, c[cls.primary]),
            sa.Index('ix_{0}_sub_id_amount_tmp'.format(child.name[:-4]), c.disb_amt, c[cls.primary]),

            sa.Index('ix_{0}_cmte_id_tmp'.format(child.name[:-4]), c.cmte_id, c[cls.primary]),
            sa.Index('ix_{0}_cmte_id_date_tmp'.format(child.name[:-4]), c.cmte_id, c.disb_dt, c[cls.primary]),
            sa.Index('ix_{0}_cmte_id_amount_tmp'.format(child.name[:-4]), c.cmte_id, c.disb_amt, c[cls.primary]),

            sa.Index(None, c.recipient_name_text, postgresql_using='gin'),
            sa.Index(None, c.disbursement_description_text, postgresql_using='gin'),
        ]

    @classmethod
    def update_child(cls, child):
        cmd = 'alter table {0} alter column recipient_st set statistics 1000'.format(child.name)
        db.engine.execute(cmd)
