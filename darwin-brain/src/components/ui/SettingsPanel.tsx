import { motion, AnimatePresence } from 'framer-motion';
import { useDarwinStore } from '../../store/darwinStore';

export function SettingsPanel() {
  const showSettings = useDarwinStore((state) => state.showSettings);
  const toggleSettings = useDarwinStore((state) => state.toggleSettings);
  const status = useDarwinStore((state) => state.status);

  // Visualization settings from store (now affects the display)
  const voiceEnabled = useDarwinStore((state) => state.voiceEnabled);
  const setVoiceEnabled = useDarwinStore((state) => state.setVoiceEnabled);
  const autoRotate = useDarwinStore((state) => state.autoRotate);
  const setAutoRotate = useDarwinStore((state) => state.setAutoRotate);
  const particleDensity = useDarwinStore((state) => state.particleDensity);
  const setParticleDensity = useDarwinStore((state) => state.setParticleDensity);
  const bloomIntensity = useDarwinStore((state) => state.bloomIntensity);
  const setBloomIntensity = useDarwinStore((state) => state.setBloomIntensity);

  return (
    <AnimatePresence>
      {showSettings && (
        <motion.div
          initial={{ x: 400, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 400, opacity: 0 }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="fixed right-4 top-20 bottom-4 w-96 z-40"
        >
          <div className="h-full glass rounded-2xl flex flex-col overflow-hidden">
            {/* Header */}
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xl">⚙️</span>
                <div>
                  <h3 className="font-semibold text-white">Settings</h3>
                  <p className="text-xs text-gray-400">Customize Darwin's Brain</p>
                </div>
              </div>
              <button
                onClick={toggleSettings}
                className="p-1 rounded-lg hover:bg-white/10 transition-colors"
              >
                <span className="text-gray-400">✕</span>
              </button>
            </div>

            {/* Settings Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
              {/* Darwin Status */}
              <section>
                <h4 className="text-sm font-medium text-gray-300 mb-3">Darwin Status</h4>
                <div className="glass rounded-xl p-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">State</span>
                    <span className="text-white capitalize">{status.state}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Mood</span>
                    <span className="text-white capitalize">{status.mood}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Cycle Progress</span>
                    <span className="text-white">{status.cycleProgress}%</span>
                  </div>
                </div>
              </section>

              {/* Voice Settings */}
              <section>
                <h4 className="text-sm font-medium text-gray-300 mb-3">Voice</h4>
                <div className="glass rounded-xl p-4">
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="text-sm text-gray-300">Enable Voice Responses</span>
                    <div
                      className={`w-12 h-6 rounded-full transition-colors ${
                        voiceEnabled ? 'bg-cyan-600' : 'bg-gray-600'
                      }`}
                      onClick={() => setVoiceEnabled(!voiceEnabled)}
                    >
                      <div
                        className={`w-5 h-5 rounded-full bg-white shadow-md transform transition-transform mt-0.5 ${
                          voiceEnabled ? 'translate-x-6' : 'translate-x-0.5'
                        }`}
                      />
                    </div>
                  </label>
                </div>
              </section>

              {/* Visualization Settings */}
              <section>
                <h4 className="text-sm font-medium text-gray-300 mb-3">Visualization</h4>
                <div className="glass rounded-xl p-4 space-y-4">
                  {/* Auto Rotate */}
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="text-sm text-gray-300">Auto Rotate</span>
                    <div
                      className={`w-12 h-6 rounded-full transition-colors ${
                        autoRotate ? 'bg-cyan-600' : 'bg-gray-600'
                      }`}
                      onClick={() => setAutoRotate(!autoRotate)}
                    >
                      <div
                        className={`w-5 h-5 rounded-full bg-white shadow-md transform transition-transform mt-0.5 ${
                          autoRotate ? 'translate-x-6' : 'translate-x-0.5'
                        }`}
                      />
                    </div>
                  </label>

                  {/* Particle Density */}
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-gray-300">Particle Density</span>
                      <span className="text-gray-400">{particleDensity}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={particleDensity}
                      onChange={(e) => setParticleDensity(Number(e.target.value))}
                      className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                    />
                  </div>

                  {/* Bloom Intensity */}
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-gray-300">Bloom Intensity</span>
                      <span className="text-gray-400">{bloomIntensity}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={bloomIntensity}
                      onChange={(e) => setBloomIntensity(Number(e.target.value))}
                      className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                    />
                  </div>
                </div>
              </section>

              {/* About */}
              <section>
                <h4 className="text-sm font-medium text-gray-300 mb-3">About</h4>
                <div className="glass rounded-xl p-4">
                  <div className="text-center">
                    <span className="text-3xl">🧠</span>
                    <h5 className="text-white font-medium mt-2">Darwin's Brain</h5>
                    <p className="text-xs text-gray-400 mt-1">
                      3D Consciousness Visualization
                    </p>
                    <p className="text-xs text-gray-500 mt-2">
                      Version 3.0 | React Three Fiber
                    </p>
                  </div>
                </div>
              </section>

              {/* Connection Info */}
              <section>
                <h4 className="text-sm font-medium text-gray-300 mb-3">Connection</h4>
                <div className="glass rounded-xl p-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Backend</span>
                    <span className="text-gray-300">localhost:8000</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">WebSocket</span>
                    <span className="text-gray-300">ws://localhost:8000/ws</span>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default SettingsPanel;
