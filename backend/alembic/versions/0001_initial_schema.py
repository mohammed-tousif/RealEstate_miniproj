"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-10-14 08:24:57.282272
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum CHECK constraints are created by the sa.Enum(create_constraint=True) columns.
    op.create_table('amenities',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=60), nullable=False),
    sa.Column('label', sa.String(length=120), nullable=False),
    sa.Column('category', sa.Enum('education', 'health', 'transport', 'utilities', 'shopping', 'agriculture', 'recreation', name='amenity_category', native_enum=False, create_constraint=True, length=40), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_amenities')),
    sa.UniqueConstraint('code', name=op.f('uq_amenities_code'))
    )
    op.create_table('localities',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('locality_name', sa.String(length=120), nullable=False),
    sa.Column('city', sa.String(length=80), nullable=False),
    sa.Column('district', sa.String(length=80), nullable=False),
    sa.Column('state', sa.String(length=80), nullable=False),
    sa.Column('center_lat', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('center_lng', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('coordinates_approximate', sa.Boolean(), nullable=False),
    sa.Column('is_rural', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_localities')),
    sa.UniqueConstraint('locality_name', 'city', name='uq_localities_name_city')
    )
    with op.batch_alter_table('localities', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_localities_city'), ['city'], unique=False)

    op.create_table('model_metadata',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('model_name', sa.String(length=80), nullable=False),
    sa.Column('model_version', sa.String(length=40), nullable=False),
    sa.Column('training_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('dataset_version', sa.String(length=80), nullable=False),
    sa.Column('feature_schema', sa.JSON(), nullable=False),
    sa.Column('evaluation_metrics', sa.JSON(), nullable=False),
    sa.Column('trained_on_synthetic', sa.Boolean(), nullable=False),
    sa.Column('artifact_path', sa.String(length=300), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_model_metadata'))
    )
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('password_hash', sa.String(length=200), nullable=True),
    sa.Column('auth_provider_id', sa.String(length=200), nullable=True),
    sa.Column('role', sa.Enum('buyer', 'seller', 'admin', name='user_role', native_enum=False, create_constraint=True, length=40), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_demo_account', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)

    op.create_table('properties',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('owner_id', sa.Uuid(), nullable=False),
    sa.Column('locality_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=160), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('property_type', sa.Enum('residential_plot', 'independent_house', 'agricultural_land', 'commercial_plot', 'commercial_building', name='property_type', native_enum=False, create_constraint=True, length=40), nullable=False),
    sa.Column('intended_land_use', sa.Enum('residential', 'agricultural', 'commercial', 'mixed', 'unknown', name='intended_land_use', native_enum=False, create_constraint=True, length=40), nullable=False),
    sa.Column('land_classification', sa.Enum('agricultural', 'non_agricultural_residential', 'non_agricultural_commercial', 'unknown', name='land_classification', native_enum=False, create_constraint=True, length=40), nullable=False),
    sa.Column('conversion_status', sa.Enum('converted_claimed', 'conversion_in_progress', 'not_converted', 'not_applicable', 'unknown', name='conversion_status', native_enum=False, create_constraint=True, length=40), nullable=False),
    sa.Column('layout_approval_status', sa.Enum('approved_layout_claimed', 'unapproved_layout', 'not_applicable', 'unknown', name='layout_approval_status', native_enum=False, create_constraint=True, length=40), nullable=False),
    sa.Column('asking_price_inr', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('area_value', sa.Numeric(precision=16, scale=4), nullable=False),
    sa.Column('area_unit', sa.Enum('sqft', 'sqm', 'gunta', 'acre', name='area_unit', native_enum=False, create_constraint=True, length=40), nullable=False),
    sa.Column('normalized_area_sqft', sa.Numeric(precision=16, scale=4), nullable=False),
    sa.Column('plot_width_ft', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('plot_length_ft', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('road_frontage_ft', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('road_access', sa.Enum('highway', 'main_road', 'paved_internal', 'unpaved', 'no_direct_access', 'unknown', name='road_access', native_enum=False, create_constraint=True, length=40), nullable=False),
    sa.Column('is_corner_plot', sa.Boolean(), nullable=True),
    sa.Column('general_address', sa.String(length=300), nullable=True),
    sa.Column('latitude', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('longitude', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('coordinates_approximate', sa.Boolean(), nullable=False),
    sa.Column('listing_status', sa.Enum('pending', 'approved', 'rejected', 'flagged', 'archived', name='listing_status', native_enum=False, create_constraint=True, length=40), nullable=False),
    sa.Column('review_reason', sa.Text(), nullable=True),
    sa.Column('restriction_notes', sa.Text(), nullable=True),
    sa.Column('additional_notes', sa.Text(), nullable=True),
    sa.Column('relevant_authorities', sa.String(length=300), nullable=True),
    sa.Column('is_synthetic', sa.Boolean(), nullable=False),
    sa.Column('data_source', sa.String(length=80), nullable=False),
    sa.Column('source_record_id', sa.String(length=80), nullable=True),
    sa.Column('last_verified_on', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('area_value > 0', name=op.f('ck_properties_area_positive')),
    sa.CheckConstraint('asking_price_inr > 0', name=op.f('ck_properties_price_positive')),
    sa.CheckConstraint('latitude IS NULL OR (latitude BETWEEN -90 AND 90)', name=op.f('ck_properties_lat_range')),
    sa.CheckConstraint('longitude IS NULL OR (longitude BETWEEN -180 AND 180)', name=op.f('ck_properties_lng_range')),
    sa.CheckConstraint('normalized_area_sqft > 0', name=op.f('ck_properties_norm_area_positive')),
    sa.CheckConstraint('road_frontage_ft IS NULL OR road_frontage_ft > 0', name=op.f('ck_properties_frontage_positive')),
    sa.ForeignKeyConstraint(['locality_id'], ['localities.id'], name=op.f('fk_properties_locality_id_localities'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_properties_owner_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_properties'))
    )
    with op.batch_alter_table('properties', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_properties_asking_price_inr'), ['asking_price_inr'], unique=False)
        batch_op.create_index(batch_op.f('ix_properties_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_properties_is_synthetic'), ['is_synthetic'], unique=False)
        batch_op.create_index(batch_op.f('ix_properties_locality_id'), ['locality_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_properties_normalized_area_sqft'), ['normalized_area_sqft'], unique=False)
        batch_op.create_index(batch_op.f('ix_properties_owner_id'), ['owner_id'], unique=False)
        batch_op.create_index('ix_properties_status_type', ['listing_status', 'property_type'], unique=False)

    op.create_table('recommendation_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('session_ref', sa.String(length=80), nullable=True),
    sa.Column('input_criteria', sa.JSON(), nullable=False),
    sa.Column('engine_version', sa.String(length=40), nullable=False),
    sa.Column('result_property_ids', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_recommendation_history_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_recommendation_history'))
    )
    with op.batch_alter_table('recommendation_history', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_recommendation_history_user_id'), ['user_id'], unique=False)

    op.create_table('user_preferences',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('minimum_budget', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('maximum_budget', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('preferred_locality_ids', sa.JSON(), nullable=True),
    sa.Column('preferred_cities', sa.JSON(), nullable=True),
    sa.Column('preferred_property_types', sa.JSON(), nullable=True),
    sa.Column('objective', sa.String(length=40), nullable=True),
    sa.Column('investment_horizon_years', sa.Integer(), nullable=True),
    sa.Column('other', sa.JSON(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_preferences_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_user_preferences'))
    )
    op.create_table('favorites',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('property_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['property_id'], ['properties.id'], name=op.f('fk_favorites_property_id_properties'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_favorites_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'property_id', name=op.f('pk_favorites'))
    )
    op.create_table('property_amenities',
    sa.Column('property_id', sa.Uuid(), nullable=False),
    sa.Column('amenity_id', sa.Integer(), nullable=False),
    sa.Column('approx_distance_km', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.Column('distance_is_synthetic', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['amenity_id'], ['amenities.id'], name=op.f('fk_property_amenities_amenity_id_amenities'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['property_id'], ['properties.id'], name=op.f('fk_property_amenities_property_id_properties'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('property_id', 'amenity_id', name=op.f('pk_property_amenities'))
    )
    op.create_table('property_documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('property_id', sa.Uuid(), nullable=False),
    sa.Column('document_type', sa.Enum('rtc_pahani', 'mutation_record', 'encumbrance_certificate', 'khata', 'sale_deed', 'dc_conversion_order', 'layout_approval', 'building_plan_approval', 'commencement_certificate', 'completion_certificate', 'occupancy_certificate', 'rera_registration', name='document_type', native_enum=False, create_constraint=True, length=40), nullable=False),
    sa.Column('availability', sa.Enum('provided', 'not_provided', 'not_applicable', 'unknown', name='doc_availability', native_enum=False, create_constraint=True, length=40), nullable=False),
    sa.Column('verification_status', sa.Enum('unverified', 'pending', 'verified', 'not_applicable', name='verification_status', native_enum=False, create_constraint=True, length=40), nullable=False),
    sa.Column('storage_path', sa.String(length=300), nullable=True),
    sa.Column('verification_notes', sa.Text(), nullable=True),
    sa.Column('applicable_authority', sa.String(length=200), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['property_id'], ['properties.id'], name=op.f('fk_property_documents_property_id_properties'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_property_documents')),
    sa.UniqueConstraint('property_id', 'document_type', name='uq_property_documents_prop_type')
    )
    with op.batch_alter_table('property_documents', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_property_documents_property_id'), ['property_id'], unique=False)

    op.create_table('property_images',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('property_id', sa.Uuid(), nullable=False),
    sa.Column('storage_path', sa.String(length=300), nullable=False),
    sa.Column('content_type', sa.String(length=40), nullable=False),
    sa.Column('ordering', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['property_id'], ['properties.id'], name=op.f('fk_property_images_property_id_properties'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_property_images'))
    )
    with op.batch_alter_table('property_images', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_property_images_property_id'), ['property_id'], unique=False)

    # ### end Alembic commands ###


def downgrade() -> None:
    # Enum CHECK constraints are created by the sa.Enum(create_constraint=True) columns.
    with op.batch_alter_table('property_images', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_property_images_property_id'))

    op.drop_table('property_images')
    with op.batch_alter_table('property_documents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_property_documents_property_id'))

    op.drop_table('property_documents')
    op.drop_table('property_amenities')
    op.drop_table('favorites')
    op.drop_table('user_preferences')
    with op.batch_alter_table('recommendation_history', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_recommendation_history_user_id'))

    op.drop_table('recommendation_history')
    with op.batch_alter_table('properties', schema=None) as batch_op:
        batch_op.drop_index('ix_properties_status_type')
        batch_op.drop_index(batch_op.f('ix_properties_owner_id'))
        batch_op.drop_index(batch_op.f('ix_properties_normalized_area_sqft'))
        batch_op.drop_index(batch_op.f('ix_properties_locality_id'))
        batch_op.drop_index(batch_op.f('ix_properties_is_synthetic'))
        batch_op.drop_index(batch_op.f('ix_properties_created_at'))
        batch_op.drop_index(batch_op.f('ix_properties_asking_price_inr'))

    op.drop_table('properties')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
    op.drop_table('model_metadata')
    with op.batch_alter_table('localities', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_localities_city'))

    op.drop_table('localities')
    op.drop_table('amenities')
    # ### end Alembic commands ###
