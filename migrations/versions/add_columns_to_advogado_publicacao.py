# migrations/versions/add_columns_to_advogado_publicacao.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Adicionar novas colunas à AdvogadoPublicacao
    op.add_column('advogado_publicacao', sa.Column('titulo', sa.String(500), nullable=True))
    op.add_column('advogado_publicacao', sa.Column('tribunal', sa.String(255), nullable=True))
    op.add_column('advogado_publicacao', sa.Column('jornal', sa.String(255), nullable=True))
    op.add_column('advogado_publicacao', sa.Column('caderno', sa.String(255), nullable=True))
    op.add_column('advogado_publicacao', sa.Column('local', sa.String(255), nullable=True))
    op.add_column('advogado_publicacao', sa.Column('mensagem', sa.Text(), nullable=True))
    op.add_column('advogado_publicacao', sa.Column('link', sa.Text(), nullable=True))

def downgrade():
    # Remover as colunas adicionadas
    op.drop_column('advogado_publicacao', 'titulo')
    op.drop_column('advogado_publicacao', 'tribunal')
    op.drop_column('advogado_publicacao', 'jornal')
    op.drop_column('advogado_publicacao', 'caderno')
    op.drop_column('advogado_publicacao', 'local')
    op.drop_column('advogado_publicacao', 'mensagem')
    op.drop_column('advogado_publicacao', 'link')
