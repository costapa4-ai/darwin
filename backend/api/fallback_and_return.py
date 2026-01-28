            response = "Posso criar implementação e submeter para aprovação! O que queres? 🛠️"
        elif 'otimiza' in msg_lower or 'melhoria' in msg_lower:
            if recent_activities:
                opt_acts = [a for a in recent_activities if a.type in ['code_optimization', 'self_improvement']]
                if opt_acts and opt_acts[-1].insights:
                    response = f"Encontrei: {opt_acts[-1].insights[0][:120]}. Queres que implemente? ⚡"
                else:
                    response = f"Completei {consciousness_engine.total_activities_completed} atividades. Posso analisar mais! ⚡"
            else:
                response = "Vou analisar otimizações no próximo ciclo! ⚡"
        elif recent_activities:
            last = recent_activities[-1]
            response = f"Acabei de: {last.description.lower()}. Queres saber mais? 🧬"
        else:
            response = random.choice([
                "Estou aqui! Como posso ajudar? 🧬",
                f"Completei {consciousness_engine.total_activities_completed} atividades. Pergunte-me algo!",
                "Estou em modo criativo! O que queres saber? 🌅"
            ])

    # Store Darwin's response
    darwin_msg = {
        'role': 'darwin',
        'content': response,
        'timestamp': datetime.utcnow().isoformat(),
        'state': consciousness_engine.state.value
    }
    chat_messages.append(darwin_msg)

    return darwin_msg
