import ezdxf
import os

def create_poste_generico(filepath):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    # Bloco em (0,0)
    msp.add_circle((0, 0), 0.5, dxfattribs={'layer': 'SISRUA_BLOCO'})
    msp.add_line((-0.5, 0), (0.5, 0), dxfattribs={'layer': 'SISRUA_BLOCO'})
    msp.add_line((0, -0.5), (0, 0.5), dxfattribs={'layer': 'SISRUA_BLOCO'})
    doc.layers.add(name='SISRUA_BLOCO', color=7)
    doc.saveas(filepath)
    print(f"Bloco 'Poste Genérico' criado em {filepath}")

def create_medidor_generico(filepath):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    # Quadrado centrado em (0,0) de lado 1
    msp.add_lwpolyline([(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)], close=True, dxfattribs={'layer': 'SISRUA_BLOCO'})
    doc.layers.add(name='SISRUA_BLOCO', color=7)
    doc.saveas(filepath)
    print(f"Bloco 'Medidor Genérico' criado em {filepath}")

def create_caixa_generica(filepath):
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    # Quadrado com linha diagonal
    msp.add_lwpolyline([(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)], close=True, dxfattribs={'layer': 'SISRUA_BLOCO'})
    msp.add_line((-0.5, -0.5), (0.5, 0.5), dxfattribs={'layer': 'SISRUA_BLOCO'})
    doc.layers.add(name='SISRUA_BLOCO', color=7)
    doc.saveas(filepath)
    print(f"Bloco 'Caixa Genérica' criado em {filepath}")

if __name__ == '__main__':
    # A pasta 'Blocks' na raiz é usada para a criação inicial.
    blocks_dir = 'Blocks'
    if not os.path.exists(blocks_dir):
        os.makedirs(blocks_dir)
        
    create_poste_generico(os.path.join(blocks_dir, 'POSTE_GENERICO.dxf'))
    create_medidor_generico(os.path.join(blocks_dir, 'MEDIDOR_GENERICO.dxf'))
    create_caixa_generica(os.path.join(blocks_dir, 'CAIXA_GENERICA.dxf'))
