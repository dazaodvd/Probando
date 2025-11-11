import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Mic, MicOff, Settings, Paperclip, Sun, Moon, Trash2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Web Speech API para reconocimiento de voz
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = SpeechRecognition ? new SpeechRecognition() : null;

if (recognition) {
  recognition.lang = 'es-ES';
  recognition.continuous = false;
  recognition.interimResults = false;
}

export default function ChatAssistant() {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [config, setConfig] = useState({
    assistant_name: 'Asistente IA',
    model: 'gemini-2.0-flash-exp',
    theme: 'dark',
    has_api_key: false,
    document_count: 0
  });
  const [isDark, setIsDark] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [settingsForm, setSettingsForm] = useState({
    assistant_name: '',
    api_key: '',
    model: ''
  });
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  
  const chatContainerRef = useRef(null);
  const fileInputRef = useRef(null);
  const sessionId = useRef(`session-${Date.now()}`);
  
  // Cargar configuración al inicio
  useEffect(() => {
    loadConfig();
  }, []);
  
  // Auto-scroll al agregar mensajes
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);
  
  // Configurar reconocimiento de voz
  useEffect(() => {
    if (recognition) {
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInputText(transcript);
        setIsListening(false);
        handleSendMessage(transcript);
      };
      
      recognition.onerror = (event) => {
        console.error('Error en reconocimiento de voz:', event.error);
        setIsListening(false);
        addMessage('Lo siento, no pude entender lo que dijiste.', false, false);
      };
      
      recognition.onend = () => {
        setIsListening(false);
      };
    }
  }, []);
  
  const loadConfig = async () => {
    try {
      const response = await axios.get(`${API}/assistant/config`);
      setConfig(response.data);
      setIsDark(response.data.theme === 'dark');
      setSettingsForm({
        assistant_name: response.data.assistant_name,
        api_key: '',
        model: response.data.model
      });
    } catch (error) {
      console.error('Error al cargar configuración:', error);
    }
  };
  
  const addMessage = (text, isUser, speak = true) => {
    const newMessage = {
      id: Date.now(),
      text,
      isUser,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, newMessage]);
    
    // Text-to-Speech
    if (!isUser && speak && voiceEnabled && 'speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'es-ES';
      utterance.rate = 0.9;
      window.speechSynthesis.speak(utterance);
    }
  };
  
  const handleSendMessage = async (message = null) => {
    const textToSend = message || inputText.trim();
    if (!textToSend) return;
    
    // Agregar mensaje del usuario
    addMessage(textToSend, true, false);
    setInputText('');
    setIsThinking(true);
    
    try {
      const response = await axios.post(`${API}/assistant/chat`, {
        message: textToSend,
        session_id: sessionId.current
      });
      
      addMessage(response.data.response, false, true);
    } catch (error) {
      console.error('Error al enviar mensaje:', error);
      addMessage('Lo siento, hubo un error al procesar tu mensaje.', false, false);
    } finally {
      setIsThinking(false);
    }
  };
  
  const handleVoiceInput = () => {
    if (!recognition) {
      alert('Tu navegador no soporta reconocimiento de voz.');
      return;
    }
    
    if (isListening) {
      recognition.stop();
      setIsListening(false);
    } else {
      setIsListening(true);
      recognition.start();
    }
  };
  
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    if (!file.name.endsWith('.pdf') && !file.name.endsWith('.txt')) {
      alert('Solo se admiten archivos .pdf y .txt');
      return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    addMessage(`Cargando documento: ${file.name}...`, true, false);
    
    try {
      const response = await axios.post(`${API}/assistant/document/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      addMessage(response.data.message, false, true);
      loadConfig(); // Actualizar contador de documentos
    } catch (error) {
      console.error('Error al cargar documento:', error);
      addMessage('Error al cargar el documento. Por favor, intenta de nuevo.', false, false);
    }
    
    // Reset input
    event.target.value = '';
  };
  
  const handleClearDocuments = async () => {
    if (!window.confirm('¿Estás seguro de que quieres eliminar todos los documentos cargados?')) {
      return;
    }
    
    try {
      const response = await axios.delete(`${API}/assistant/document/clear`);
      addMessage(response.data.message, false, true);
      loadConfig();
    } catch (error) {
      console.error('Error al limpiar documentos:', error);
      addMessage('Error al eliminar los documentos.', false, false);
    }
  };
  
  const handleSaveSettings = async () => {
    try {
      const updateData = {
        assistant_name: settingsForm.assistant_name || undefined,
        api_key: settingsForm.api_key || undefined,
        model: settingsForm.model || undefined
      };
      
      const response = await axios.post(`${API}/assistant/config`, updateData);
      
      if (response.data.success) {
        alert('Configuración actualizada correctamente');
        setShowSettings(false);
        loadConfig();
      }
    } catch (error) {
      console.error('Error al actualizar configuración:', error);
      alert('Error al actualizar la configuración. Verifica la API key.');
    }
  };
  
  const toggleTheme = () => {
    setIsDark(!isDark);
  };
  
  // Estilos dinámicos según el tema
  const bgPrimary = isDark ? 'bg-gray-900' : 'bg-gray-50';
  const bgSecondary = isDark ? 'bg-gray-800' : 'bg-white';
  const bgInput = isDark ? 'bg-gray-700' : 'bg-gray-100';
  const textPrimary = isDark ? 'text-white' : 'text-gray-900';
  const textSecondary = isDark ? 'text-gray-300' : 'text-gray-700';
  const bubbleUser = isDark ? 'bg-blue-600' : 'bg-blue-500';
  const bubbleAssistant = isDark ? 'bg-gray-700' : 'bg-gray-200';
  const bubbleTextAssistant = isDark ? 'text-white' : 'text-gray-900';
  
  return (
    <div className={`flex flex-col h-screen ${bgPrimary} ${textPrimary} transition-colors duration-300`}>
      {/* Header */}
      <div className={`${bgSecondary} shadow-lg px-4 py-3 flex items-center justify-between`}>
        <h1 className="text-xl font-bold">{config.assistant_name}</h1>
        <div className="flex items-center gap-2">
          {config.document_count > 0 && (
            <span className={`text-sm ${textSecondary} px-2 py-1 rounded-full ${bgInput}`}>
              {config.document_count} docs
            </span>
          )}
          <button
            onClick={toggleTheme}
            className={`p-2 rounded-full hover:${bgInput} transition-colors`}
            title="Cambiar tema"
          >
            {isDark ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`p-2 rounded-full hover:${bgInput} transition-colors`}
            title="Configuración"
          >
            <Settings size={20} />
          </button>
        </div>
      </div>
      
      {/* Settings Panel */}
      {showSettings && (
        <div className={`${bgSecondary} border-b ${isDark ? 'border-gray-700' : 'border-gray-200'} p-4`}>
          <h2 className="text-lg font-semibold mb-3">Ajustes del Asistente</h2>
          <div className="space-y-3">
            <div>
              <label className={`block text-sm ${textSecondary} mb-1`}>Nombre del Asistente:</label>
              <input
                type="text"
                value={settingsForm.assistant_name}
                onChange={(e) => setSettingsForm({...settingsForm, assistant_name: e.target.value})}
                className={`w-full px-3 py-2 rounded-lg ${bgInput} ${textPrimary} border-0 focus:ring-2 focus:ring-blue-500`}
              />
            </div>
            <div>
              <label className={`block text-sm ${textSecondary} mb-1`}>Clave de Gemini API:</label>
              <input
                type="password"
                value={settingsForm.api_key}
                onChange={(e) => setSettingsForm({...settingsForm, api_key: e.target.value})}
                placeholder="Dejar vacío para no cambiar"
                className={`w-full px-3 py-2 rounded-lg ${bgInput} ${textPrimary} border-0 focus:ring-2 focus:ring-blue-500`}
              />
            </div>
            <div>
              <label className={`block text-sm ${textSecondary} mb-1`}>Modelo de IA:</label>
              <input
                type="text"
                value={settingsForm.model}
                onChange={(e) => setSettingsForm({...settingsForm, model: e.target.value})}
                className={`w-full px-3 py-2 rounded-lg ${bgInput} ${textPrimary} border-0 focus:ring-2 focus:ring-blue-500`}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="voice-enabled"
                checked={voiceEnabled}
                onChange={(e) => setVoiceEnabled(e.target.checked)}
                className="w-4 h-4"
              />
              <label htmlFor="voice-enabled" className={`text-sm ${textSecondary}`}>
                Activar síntesis de voz
              </label>
            </div>
            <div className="flex justify-between items-center pt-2">
              <button
                onClick={handleClearDocuments}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
                disabled={config.document_count === 0}
              >
                <Trash2 size={16} />
                Limpiar Documentos
              </button>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowSettings(false)}
                  className={`px-4 py-2 ${bgInput} rounded-lg hover:opacity-80 transition-opacity`}
                >
                  Cancelar
                </button>
                <button
                  onClick={handleSaveSettings}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Guardar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Chat Container */}
      <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className={`text-center ${textSecondary} mt-10`}>
            <p className="text-lg">¡Hola! Soy tu asistente de IA.</p>
            <p className="text-sm mt-2">Escribe un mensaje o usa el micrófono para comenzar.</p>
          </div>
        )}
        
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start gap-3 ${msg.isUser ? 'flex-row-reverse' : 'flex-row'}`}
          >
            {/* Avatar */}
            <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
              msg.isUser ? 'bg-cyan-800' : 'bg-blue-700'
            }`}>
              {msg.isUser ? (
                <span className="text-white font-semibold text-sm">TÚ</span>
              ) : (
                <span className="text-white text-lg">🤖</span>
              )}
            </div>
            
            {/* Message Bubble */}
            <div
              className={`max-w-[70%] px-4 py-3 rounded-2xl shadow-md ${
                msg.isUser
                  ? `${bubbleUser} text-white`
                  : `${bubbleAssistant} ${bubbleTextAssistant}`
              }`}
              style={{
                wordWrap: 'break-word',
                whiteSpace: 'pre-wrap'
              }}
            >
              {msg.text}
            </div>
          </div>
        ))}
        
        {isThinking && (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-700 flex items-center justify-center">
              <span className="text-white text-lg">🤖</span>
            </div>
            <div className={`px-4 py-3 rounded-2xl ${bubbleAssistant}`}>
              <div className="flex gap-1">
                <span className="animate-bounce">●</span>
                <span className="animate-bounce" style={{animationDelay: '0.1s'}}>●</span>
                <span className="animate-bounce" style={{animationDelay: '0.2s'}}>●</span>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Listening Indicator */}
      {isListening && (
        <div className="px-4 pb-2 text-center">
          <span className="text-blue-500 font-semibold animate-pulse">Escuchando...</span>
        </div>
      )}
      
      {/* Input Container */}
      <div className="p-4">
        <div className={`${bgInput} rounded-full px-3 py-2 flex items-center gap-2 shadow-lg`}>
          {/* File Upload */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt"
            onChange={handleFileUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="p-2 hover:bg-gray-600 rounded-full transition-colors"
            title="Cargar documento (PDF/TXT)"
          >
            <Paperclip size={20} />
          </button>
          
          {/* Voice Input */}
          <button
            onClick={handleVoiceInput}
            className={`p-2 rounded-full transition-colors ${
              isListening ? 'bg-red-500 hover:bg-red-600' : 'hover:bg-gray-600'
            }`}
            title="Reconocimiento de voz"
          >
            {isListening ? <MicOff size={20} /> : <Mic size={20} />}
          </button>
          
          {/* Text Input */}
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Escribe tu mensaje o comando..."
            className={`flex-1 bg-transparent border-0 outline-none ${textPrimary} placeholder-gray-500`}
          />
          
          {/* Send Button */}
          <button
            onClick={() => handleSendMessage()}
            disabled={!inputText.trim()}
            className="p-2 bg-blue-600 hover:bg-blue-700 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}
