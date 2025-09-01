import sys
import os
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any

# --- IMPORTAÇÕES DO FIREBASE ---
import firebase_admin
from firebase_admin import credentials, firestore

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QTabWidget, QMessageBox,
    QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDateEdit, QSpinBox, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QCheckBox, QFileDialog, QTextEdit, QGroupBox
)

try:
    import pandas as pd
except Exception:
    pd = None

# ------------------------------
# Funções Auxiliares
# ------------------------------

STATUS_CORES = {
    "FINALIZADO": QColor(198, 239, 206),
    "ANÁLISE": QColor(255, 242, 204),
    "EM ABERTO": QColor(221, 235, 247),
}

def dias_restantes(vencimento: date) -> int:
    return (vencimento - date.today()).days

def msg(parent, title, text, icon=QMessageBox.Information):
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(icon)
    box.exec_()

# ------------------------------
# Janela Principal
# ------------------------------

class AppPA(QMainWindow):
    # Modificado para receber a ligação à base de dados
    def __init__(self, db_client):
        super().__init__()
        self.setWindowTitle("Gestor de P.A – Colaborativo (com Firebase)")
        self.resize(1200, 720)

        # Guarda a referência ao cliente e à coleção do Firestore
        self.db = db_client
        self.colecao_ref = self.db.collection('registros_pa')

        self.registros: List[Dict[str, Any]] = []
        self.registro_em_edicao_id = None

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._build_tab_cadastro()
        self._build_tab_registros()
        self._build_tab_historico()

        self._iniciar_listener_firestore()
        self._verificar_prazos_vencidos()

    def _iniciar_listener_firestore(self):
        """Cria um 'ouvinte' que atualiza a tabela sempre que há uma mudança no banco de dados."""
        self.listener = self.colecao_ref.on_snapshot(self._on_snapshot_callback)

    def _on_snapshot_callback(self, doc_snapshot, changes, read_time):
        """Função chamada automaticamente pelo Firebase quando os dados mudam."""
        print("Recebida atualização do Firestore...")
        self.registros = []
        for doc in doc_snapshot:
            dados = doc.to_dict()
            dados['id'] = doc.id
            
            if 'ABERTURA' in dados and isinstance(dados['ABERTURA'], datetime):
                dados['ABERTURA'] = dados['ABERTURA'].date()
            if 'VENCIMENTO' in dados and isinstance(dados['VENCIMENTO'], datetime):
                dados['VENCIMENTO'] = dados['VENCIMENTO'].date()
            
            self.registros.append(dados)
        
        self.registros.sort(key=lambda r: r.get('CRIADO_EM', datetime.min), reverse=True)
        self._atualiza_tabela()
        self._append_historico("Dados sincronizados com a nuvem.")

    def closeEvent(self, event):
        """Garante que o listener seja desativado ao fechar."""
        if hasattr(self, 'listener'):
            self.listener.unsubscribe()
        event.accept()

    # ---------- Aba: Cadastro ----------
    def _build_tab_cadastro(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form_box = QGroupBox("Novo Registo")
        form_layout = QFormLayout(form_box)

        self.ed_id_sgd = QLineEdit()
        self.ed_cidade = QLineEdit()
        self.cb_base = QComboBox(); self.cb_base.addItems(["", "SUL", "BRA", "ISP", "ABC"])
        self.cb_base.setEditable(True)
        self.ed_caixa_mapa = QLineEdit()
        self.ed_caixa_sistema = QLineEdit()
        self.sp_qtd_hp = QSpinBox(); self.sp_qtd_hp.setRange(0, 1_000_000)
        self.ed_pa = QLineEdit()
        self.ed_aberto_por = QLineEdit()
        self.dt_abertura = QDateEdit(); self.dt_abertura.setCalendarPopup(True)
        self.dt_abertura.setDate(QDate.currentDate())
        self.dt_vencimento = QDateEdit(); self.dt_vencimento.setCalendarPopup(True)
        self.dt_vencimento.setDate(QDate.currentDate())
        self.sp_tempo_restante = QSpinBox(); self.sp_tempo_restante.setRange(-9999, 9999)
        self.sp_tempo_restante.setReadOnly(True)
        self.sp_tempo_restante.setButtonSymbols(self.sp_tempo_restante.NoButtons)
        self.cb_status = QComboBox(); self.cb_status.addItems(["EM ABERTO", "ANÁLISE", "FINALIZADO"])
        self.cb_status.setEditable(True)
        self.cb_concluido = QComboBox(); self.cb_concluido.addItems(["", "SIM", "NÃO"])
        self.cb_concluido.setEditable(True)
        self.cb_pa_tipo = QComboBox()
        self.cb_pa_tipo.addItems(["", "P.A 3 dias", "P.A 7 dias", "P.A 3 e 7 dias"])

        self.dt_abertura.dateChanged.connect(self._atualiza_vencimento_automatico)
        self.cb_pa_tipo.currentIndexChanged.connect(self._atualiza_vencimento_automatico)
        self.dt_vencimento.dateChanged.connect(self._atualiza_tempo_restante)
        self._atualiza_tempo_restante()

        form_layout.addRow("ID SGD:", self.ed_id_sgd)
        form_layout.addRow("CIDADE:", self.ed_cidade)
        form_layout.addRow("BASE GED:", self.cb_base)
        form_layout.addRow("CAIXA MAPA:", self.ed_caixa_mapa)
        form_layout.addRow("CAIXA SISTEMA:", self.ed_caixa_sistema)
        form_layout.addRow("Quantidade HP:", self.sp_qtd_hp)
        form_layout.addRow("PA:", self.ed_pa)
        form_layout.addRow("ABERTO POR:", self.ed_aberto_por)
        form_layout.addRow("ABERTURA:", self.dt_abertura)
        form_layout.addRow("VENCIMENTO:", self.dt_vencimento)
        form_layout.addRow("TEMPO RESTANTE (dias):", self.sp_tempo_restante)
        form_layout.addRow("STATUS:", self.cb_status)
        form_layout.addRow("CONCLUSÃO:", self.cb_concluido)
        form_layout.addRow("Necessidade:", self.cb_pa_tipo)

        btns = QWidget(); h = QHBoxLayout(btns); h.setContentsMargins(0,0,0,0)
        self.bt_salvar = QPushButton("Salvar registo")
        self.bt_limpar = QPushButton("Limpar")
        self.bt_salvar.clicked.connect(self._salvar_registro)
        self.bt_limpar.clicked.connect(self._limpar_form)
        h.addStretch(1); h.addWidget(self.bt_limpar); h.addWidget(self.bt_salvar)

        layout.addWidget(form_box)
        layout.addWidget(btns)
        layout.addStretch()

        self.tabs.addTab(tab, "Cadastro")

    def _atualiza_tempo_restante(self):
        d = self.dt_vencimento.date().toPyDate()
        self.sp_tempo_restante.setValue(dias_restantes(d))

    def _atualiza_vencimento_automatico(self):
        base_date = self.dt_abertura.date().toPyDate()
        tipo_pa = self.cb_pa_tipo.currentText()
        dias_a_adicionar = 0
        if tipo_pa == "P.A 3 dias":
            dias_a_adicionar = 3
        elif tipo_pa in ["P.A 7 dias", "P.A 3 e 7 dias"]:
            dias_a_adicionar = 7
        if dias_a_adicionar > 0:
            nova_data_vencimento = base_date + timedelta(days=dias_a_adicionar)
            self.dt_vencimento.setDate(QDate(nova_data_vencimento))

    def _validar(self) -> bool:
        obrigatorios = {
            "ID SGD": self.ed_id_sgd.text().strip(),
            "Cidade": self.ed_cidade.text().strip(),
        }
        faltando = [k for k, v in obrigatorios.items() if not v]
        if faltando:
            msg(self, "Campos obrigatórios", f"Preencha: {', '.join(faltando)}", QMessageBox.Warning)
            return False
        return True

    def _coletar_form(self) -> Dict[str, Any]:
        abertura_dt = datetime.combine(self.dt_abertura.date().toPyDate(), datetime.min.time())
        vencimento_dt = datetime.combine(self.dt_vencimento.date().toPyDate(), datetime.min.time())

        return {
            "ID SGD": self.ed_id_sgd.text().strip(),
            "CIDADE": self.ed_cidade.text().strip(),
            "BASE GED": self.cb_base.currentText().strip(),
            "CAIXA MAPA": self.ed_caixa_mapa.text().strip(),
            "CAIXA SISTEMA": self.ed_caixa_sistema.text().strip(),
            "Quantidade HP": int(self.sp_qtd_hp.value()),
            "PA": self.ed_pa.text().strip(),
            "ABERTO POR": self.ed_aberto_por.text().strip(),
            "ABERTURA": abertura_dt,
            "VENCIMENTO": vencimento_dt,
            "TEMPO RESTANTE": int(self.sp_tempo_restante.value()),
            "STATUS": self.cb_status.currentText().strip(),
            "CONCLUSAO": self.cb_concluido.currentText().strip(),
            "TIPO PA": self.cb_pa_tipo.currentText().strip(),
            "CRIADO_EM": datetime.now(),
        }

    def _salvar_registro(self):
        if not self._validar():
            return
        
        dados = self._coletar_form()
        
        try:
            if self.registro_em_edicao_id is None:
                self.colecao_ref.add(dados)
                self._append_historico(f"Novo registo salvo na nuvem – ID SGD: {dados['ID SGD']}")
                msg(self, "Sucesso", "Registo adicionado ao quadro.")
            else:
                self.colecao_ref.document(self.registro_em_edicao_id).set(dados)
                self._append_historico(f"Registo atualizado na nuvem – ID SGD: {dados['ID SGD']}")
                msg(self, "Sucesso", "Registo atualizado com sucesso.")
            
            self._limpar_form()
        except Exception as e:
            msg(self, "Erro de Base de Dados", f"Falha ao salvar os dados: {e}", QMessageBox.Critical)

    def _limpar_form(self):
        self.ed_id_sgd.clear()
        self.ed_cidade.clear()
        self.cb_base.setCurrentIndex(0)
        self.ed_caixa_mapa.clear()
        self.ed_caixa_sistema.clear()
        self.sp_qtd_hp.setValue(0)
        self.ed_pa.clear()
        self.ed_aberto_por.clear()
        self.dt_abertura.setDate(QDate.currentDate())
        self.dt_vencimento.setDate(QDate.currentDate())
        self.cb_status.setCurrentIndex(0)
        self.cb_concluido.setCurrentIndex(0)
        self.cb_pa_tipo.setCurrentIndex(0)
        self._atualiza_tempo_restante()
        self.registro_em_edicao_id = None
        self.bt_salvar.setText("Salvar registo")

    # ---------- Aba: Registos ----------
    def _build_tab_registros(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        top = QWidget(); h = QHBoxLayout(top); h.setContentsMargins(0,0,0,0)
        self.bt_exportar = QPushButton("Exportar para Excel…")
        self.bt_exportar.clicked.connect(self._exportar_excel)
        self.bt_excluir = QPushButton("Excluir selecionados")
        self.bt_excluir.clicked.connect(self._excluir_selecionados)
        self.bt_recalc = QPushButton("Recalcular prazos")
        self.bt_recalc.clicked.connect(self._recalcular_prazos)
        h.addWidget(self.bt_exportar); h.addWidget(self.bt_excluir); h.addWidget(self.bt_recalc); h.addStretch(1)

        self.tbl = QTableWidget(0, 14)
        headers = [
            "ID SGD","CIDADE","BASE GED","CAIXA MAPA","CAIXA SISTEMA","Quantidade HP",
            "PA","ABERTO POR","ABERTURA","VENCIMENTO","TEMPO RESTANTE","STATUS",
            "CONCLUSAO","TIPO PA"
        ]
        self.tbl.setHorizontalHeaderLabels(headers)
        self.tbl.setSortingEnabled(True)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(self.tbl.SelectRows)
        self.tbl.setEditTriggers(self.tbl.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.cellDoubleClicked.connect(self._carregar_registro_para_edicao)

        layout.addWidget(top)
        layout.addWidget(self.tbl)

        self.tabs.addTab(tab, "Registos")

    def _carregar_registro_para_edicao(self, row, column):
        dados = self.registros[row]
        self.registro_em_edicao_id = dados.get('id')
        
        self.ed_id_sgd.setText(dados.get("ID SGD",""))
        self.ed_cidade.setText(dados.get("CIDADE",""))
        self.cb_base.setCurrentText(dados.get("BASE GED",""))
        self.ed_caixa_mapa.setText(dados.get("CAIXA MAPA",""))
        self.ed_caixa_sistema.setText(dados.get("CAIXA SISTEMA",""))
        self.sp_qtd_hp.setValue(dados.get("Quantidade HP",0))
        self.ed_pa.setText(dados.get("PA",""))
        self.ed_aberto_por.setText(dados.get("ABERTO POR",""))
        self.dt_abertura.setDate(QDate(dados.get("ABERTURA")))
        self.dt_vencimento.setDate(QDate(dados.get("VENCIMENTO")))
        self.cb_status.setCurrentText(dados.get("STATUS",""))
        self.cb_concluido.setCurrentText(dados.get("CONCLUSAO",""))
        self.cb_pa_tipo.setCurrentText(dados.get("TIPO PA",""))
        
        self._atualiza_tempo_restante()
        self.bt_salvar.setText("Atualizar registo")
        self.tabs.setCurrentIndex(0)

    def _atualiza_tabela(self):
        self.tbl.setRowCount(len(self.registros))
        for r, reg in enumerate(self.registros):
            abertura_str = reg.get("ABERTURA").strftime("%d/%m/%Y") if reg.get("ABERTURA") else ""
            vencimento_str = reg.get("VENCIMENTO").strftime("%d/%m/%Y") if reg.get("VENCIMENTO") else ""

            valores = [
                reg.get("ID SGD",""), reg.get("CIDADE",""), reg.get("BASE GED",""),
                reg.get("CAIXA MAPA",""), reg.get("CAIXA SISTEMA",""), str(reg.get("Quantidade HP",0)),
                reg.get("PA",""), reg.get("ABERTO POR",""), abertura_str,
                vencimento_str, str(reg.get("TEMPO RESTANTE",0)),
                reg.get("STATUS",""), reg.get("CONCLUSAO",""),
                reg.get("TIPO PA", "")
            ]
            for c, v in enumerate(valores):
                item = QTableWidgetItem(v)
                if c in (5,10):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl.setItem(r, c, item)

            cor = STATUS_CORES.get(reg.get("STATUS",""))
            if cor:
                temp_item = QTableWidgetItem()
                cor_texto = temp_item.foreground().color()
                if cor_texto.lightness() > 128:
                    cor_texto = QColor("black")
                
                for c in range(self.tbl.columnCount()):
                    self.tbl.item(r,c).setBackground(cor)
                    self.tbl.item(r,c).setForeground(cor_texto)

            try:
                if reg.get("STATUS", "") != "FINALIZADO":
                    tr = int(reg.get("TEMPO RESTANTE",0))
                    if tr <= 0:
                        cor_prazo = QColor(255, 100, 100)
                    elif tr <= 3:
                        cor_prazo = QColor(255, 180, 90)
                    else:
                        cor_prazo = None
                    if cor_prazo:
                        self.tbl.item(r,10).setBackground(cor_prazo)
                        self.tbl.item(r,10).setForeground(QColor("black"))
            except Exception:
                pass

        self.tbl.resizeColumnsToContents()

    def _excluir_selecionados(self):
        linhas = sorted({i.row() for i in self.tbl.selectedIndexes()}, reverse=True)
        if not linhas:
            msg(self, "Excluir", "Nenhuma linha selecionada.")
            return
            
        for idx in linhas:
            try:
                reg_para_excluir = self.registros[idx]
                doc_id = reg_para_excluir.get('id')
                if doc_id:
                    self.colecao_ref.document(doc_id).delete()
                    self._append_historico(f"Registo removido da nuvem – ID SGD: {reg_para_excluir.get('ID SGD','')}.")
            except Exception as e:
                msg(self, "Erro de Base de Dados", f"Falha ao excluir os dados: {e}", QMessageBox.Critical)

    def _recalcular_prazos(self):
        if not self.registros:
            return

        batch = self.db.batch()
        for reg in self.registros:
            novo_tr = dias_restantes(reg["VENCIMENTO"])
            if reg.get("TEMPO RESTANTE") != novo_tr:
                doc_ref = self.colecao_ref.document(reg['id'])
                batch.update(doc_ref, {"TEMPO RESTANTE": novo_tr})
        
        try:
            batch.commit()
            self._append_historico("Recalculo de prazos executado e sincronizado com a nuvem.")
        except Exception as e:
            msg(self, "Erro de Base de Dados", f"Falha ao recalcular prazos: {e}", QMessageBox.Critical)

    def _verificar_prazos_vencidos(self):
        self._recalcular_prazos()
        vencidos = []
        for reg in self.registros:
            if reg.get("STATUS") != "FINALIZADO" and reg.get("TEMPO RESTANTE", 1) <= 0:
                vencidos.append(reg.get("ID SGD", "N/A"))
        if vencidos:
            texto_aviso = "Os seguintes registos estão com o prazo vencido ou vencendo hoje:\n\n"
            texto_aviso += "- " + "\n- ".join(vencidos)
            texto_aviso += "\n\nVerifique a aba 'Registos' para mais detalhes."
            msg(self, "Aviso de Prazos", texto_aviso, QMessageBox.Warning)


    def _exportar_excel(self):
        if pd is None:
            msg(self, "Exportar", "A exportação requer a biblioteca 'pandas'. Instale com:\n\n    pip install pandas openpyxl", QMessageBox.Warning)
            return
        if not self.registros:
            msg(self, "Exportar", "Não há registos para exportar.")
            return
        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar como", "PA_Registos.xlsx", "Planilha Excel (*.xlsx)")
        if not caminho:
            return
        linhas = []
        for r in self.registros:
            linhas.append({
                "ID SGD": r.get("ID SGD",""),
                "CIDADE": r.get("CIDADE",""),
                "BASE GED": r.get("BASE GED",""),
                "CAIXA MAPA": r.get("CAIXA MAPA",""),
                "CAIXA SISTEMA": r.get("CAIXA SISTEMA",""),
                "Quantidade HP": r.get("Quantidade HP",0),
                "PA": r.get("PA",""),
                "ABERTO POR": r.get("ABERTO POR",""),
                "ABERTURA": r.get("ABERTURA").strftime("%d/%m/%Y"),
                "VENCIMENTO": r.get("VENCIMENTO").strftime("%d/%m/%Y"),
                "TEMPO RESTANTE": r.get("TEMPO RESTANTE",0),
                "STATUS": r.get("STATUS",""),
                "CONCLUSAO": r.get("CONCLUSAO",""),
                "TIPO PA": r.get("TIPO PA", ""),
            })
        df = pd.DataFrame(linhas)
        try:
            df.to_excel(caminho, index=False)
            self._append_historico(f"Exportação realizada: {os.path.basename(caminho)}")
            msg(self, "Exportar", "Ficheiro gerado com sucesso.")
        except Exception as e:
            msg(self, "Exportar", f"Falha ao salvar: {e}", QMessageBox.Critical)

    # ---------- Aba: Histórico ----------
    def _build_tab_historico(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        tip = QLabel("Registo de ações desta sessão. Os dados são sincronizados com a nuvem (Firebase).")
        tip.setWordWrap(True)
        self.txt_hist = QTextEdit(); self.txt_hist.setReadOnly(True)
        self.txt_hist.setFont(QFont("Consolas", 10))
        layout.addWidget(tip)
        layout.addWidget(self.txt_hist)
        self.tabs.addTab(tab, "Histórico")

    def _append_historico(self, texto: str):
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.txt_hist.append(f"[{ts}] {texto}")


# ------------------------------
# Executar aplicativo
# ------------------------------
def main():
    # --- INICIALIZAÇÃO COM DIAGNÓSTICO FINAL ---
    # Primeiro, vamos criar a aplicação. Isto garante que podemos mostrar mensagens de erro.
    app = QApplication(sys.argv)
    
    # Agora, vamos tentar ligar ao Firebase e imprimir cada passo.
    try:
        print("--- A iniciar diagnóstico de caminho ---")
        
        # Determina o caminho base de forma fiável
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        key_path = os.path.join(base_path, "serviceAccountKey.json")

        print(f"Pasta base do script detetada: {base_path}")
        print(f"Caminho completo para a chave que será usado: {key_path}")
        
        # A verificação mais importante:
        key_exists = os.path.exists(key_path)
        print(f"O ficheiro da chave existe neste caminho? -> {key_exists}")
        print("--- Fim do diagnóstico ---")

        if not key_exists:
            # Lança um erro claro se o ficheiro não for encontrado
            raise FileNotFoundError(f"O ficheiro da chave '{key_path}' não foi encontrado.")

        # Se o ficheiro existe, continua com a inicialização
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
        db_client = firestore.client()

    except Exception as e:
        # Se qualquer erro acontecer, mostramos a mensagem e saímos.
        msg_erro = f"ERRO CRÍTICO: Não foi possível inicializar o Firebase.\n\n" \
                   f"Verifique as informações de diagnóstico impressas no terminal.\n\n" \
                   f"Detalhes técnicos: {e}"
        msg(None, "Erro de Inicialização", msg_erro, QMessageBox.Critical)
        return # Encerra a função main se a ligação falhar

    # Se a inicialização for bem-sucedida, o resto do código é executado
    app.setStyle("Fusion")
    style_sheet = """
        QWidget { background-color: #2E2E2E; color: #E0E0E0; font-size: 10pt; }
        QMainWindow, QTabWidget, QWidget { background-color: #2E2E2E; }
        QGroupBox { font-weight: bold; background-color: #3C3C3C; border: 1px solid #555555; border-radius: 8px; margin-top: 15px; }
        QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; color: #E0E0E0; }
        QLineEdit, QComboBox, QDateEdit, QSpinBox, QTextEdit { background-color: #3C3C3C; color: #E0E0E0; border: 1px solid #555555; border-radius: 5px; padding: 5px; }
        QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QTextEdit:focus { border: 1px solid #0078D7; }
        QComboBox QAbstractItemView, QDateEdit QAbstractItemView { background-color: #3C3C3C; color: #E0E0E0; selection-background-color: #0078D7; }
        QPushButton { background-color: #0078D7; color: white; border: none; border-radius: 5px; padding: 8px 16px; font-weight: bold; }
        QPushButton:hover { background-color: #1085E0; }
        QPushButton:pressed { background-color: #006ABC; }
        QTableWidget { background-color: #3C3C3C; gridline-color: #555555; color: #E0E0E0; alternate-background-color: #464646; }
        QHeaderView::section { background-color: #555555; color: #E0E0E0; padding: 4px; border: 1px solid #3C3C3C; font-weight: bold; }
        QTableWidget::item:selected { background-color: #0078D7; color: white; }
        QTabBar::tab { background: #3C3C3C; color: #AAAAAA; padding: 8px; border: 1px solid #555555; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
        QTabBar::tab:selected, QTabBar::tab:hover { background: #4A4A4A; color: #FFFFFF; }
        QTabWidget::pane { border: 1px solid #555555; }
        QMessageBox { background-color: #3C3C3C; }
    """
    app.setStyleSheet(style_sheet)
    
    w = AppPA(db_client)
    w.show()
    sys.exit(app.exec_())