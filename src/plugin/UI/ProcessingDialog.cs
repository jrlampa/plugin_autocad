using System;
using System.Drawing;
using System.Windows.Forms;

namespace sisRUA.UI
{
    public class ProcessingDialog : Form
    {
        private ProgressBar _progressBar;
        private Label _lblMessage;
        private System.Windows.Forms.Timer _timer;
        private int _messageIndex = 0;

        private readonly string[] _messages = new string[]
        {
            "Reticulando splines...",
            "Convencendo o AutoCAD a colaborar...",
            "Consultando o oráculo da geometria...",
            "Desembaraçando o espaguete de ruas...",
            "Garantindo que as linhas se encontram...",
            "Calculando o sentido da vida, do universo e das polylines...",
            "Carregando 'mensagem_engraçada.mp3'...",
            "Acalmando os elétrons...",
            "Invocando polígonos...",
            "Fazendo mágica acontecer...",
            "Pedindo Jonatas Lampar pra fazer café...",
            "Processando o processador...",
            "Pedindo Aumento pro Eduardo Zaluar...",
            "Reclamando do levantamento...",
            "Importando a paciência necessária...",
            "Pedindo pro Zaluar um aumento....",
            "Pedindo pro Jonatas pra fazer café...",
            "Pedindo pro Faganer ensinar a fazer georeferênciamento...",
            "Pedindo pro Fabão ensinar projeto...",
            "Perguntando pro André um troço cabuloso...",
            "Perguntando pro Santém como é que faz estudo de rede...",
            "Pendindo a Deus pra terminar...",
            "Quando o pagamento cai mesmo?...",
            "Ainda não acabou?...",
            "...",
            "404 - Mensagem não encontrada...",
            "Três patinhos foram passear...",
        };

        public ProcessingDialog()
        {
            InitializeComponent();
            InitializeTimer();
        }

        private void InitializeComponent()
        {
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.MinimizeBox = false;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.ControlBox = false; // Removendo botão X para evitar fechamento acidental
            this.Text = "sisRUA - Processando";
            this.Size = new Size(400, 150);
            this.TopMost = true; // Manter sobre o AutoCAD

            _lblMessage = new Label();
            _lblMessage.AutoSize = false;
            _lblMessage.TextAlign = ContentAlignment.MiddleCenter;
            _lblMessage.Dock = DockStyle.Top;
            _lblMessage.Height = 60;
            _lblMessage.Font = new Font("Segoe UI", 10F, FontStyle.Regular);
            _lblMessage.Text = "Iniciando processamento...";
            this.Controls.Add(_lblMessage);

            _progressBar = new ProgressBar();
            _progressBar.Style = ProgressBarStyle.Marquee; // Indeterminado
            _progressBar.MarqueeAnimationSpeed = 30;
            _progressBar.Dock = DockStyle.Top; // Mudar para Top para caber o botão embaixo
            _progressBar.Height = 30;
            this.Controls.Add(_progressBar);

            var btnCancel = new Button();
            btnCancel.Text = "CANCELAR";
            btnCancel.Dock = DockStyle.Bottom;
            btnCancel.Height = 30;
            btnCancel.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            btnCancel.Click += (s, e) => {
                WasCancelled = true;
                btnCancel.Enabled = false;
                btnCancel.Text = "Cancelando...";
                _lblMessage.Text = "Interrompendo processos...";
            };
            this.Controls.Add(btnCancel);

            // Padding para não ficar colado nas bordas
            this.Padding = new Padding(20);
        }

        public bool WasCancelled { get; private set; }

        private void InitializeTimer()
        {
            _timer = new System.Windows.Forms.Timer();
            _timer.Interval = 2500; // 2.5 segundos
            _timer.Tick += Timer_Tick;
            _timer.Start();
            
            // Já define uma mensagem aleatória inicial (exceto a primeira que é padrão "Reticulando...")
            Timer_Tick(null, null); 
        }

        private void Timer_Tick(object sender, EventArgs e)
        {
            if (_messages != null && _messages.Length > 0)
            {
                // Simples rotação ou aleatório? Vamos de sequencial cíclico + offset aleatório inicial se quisesse, 
                // mas sequencial é bom para lerem todas.
                _lblMessage.Text = _messages[_messageIndex];
                _messageIndex = (_messageIndex + 1) % _messages.Length;
            }
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            _timer?.Stop();
            _timer?.Dispose();
            base.OnFormClosing(e);
        }
    }
}
