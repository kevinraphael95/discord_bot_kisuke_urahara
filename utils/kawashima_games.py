    # ============================================================================
    # 🔹 Wrapper — exécute un mini-jeu en solo
    # ============================================================================
    async def _run_game_solo(self, game, msg_state, embed, user, timeout=60):
        """Retourne (success, clicker_id)."""
        def get_user_id():
            return user.id

        try:
            result = await asyncio.wait_for(
                game(msg_state, embed, get_user_id, self.bot),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            log.warning("[cerebral] Mini-jeu solo timeout pour %s", user)
            return False, None
        except Exception as e:
            log.exception("[cerebral] Erreur mini-jeu solo : %s", e)
            return False, None

        # Certains jeux renvoient (success, clicker_id), d'autres juste success
        if isinstance(result, tuple):
            return result
        return bool(result), None

    # ============================================================================
    # 🔹 Wrapper — exécute un mini-jeu en multi
    # ============================================================================
    async def _run_game_multi(self, game, msg_state, embed, active_players, timeout=25):
        """Retourne (winner_member_or_None, success_bool)."""
        def get_user_id():
            # None → accepte tous les joueurs actifs
            return None

        try:
            result = await asyncio.wait_for(
                game(msg_state, embed, get_user_id, self.bot),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None, False
        except Exception as e:
            log.exception("[cerebral] Erreur mini-jeu multi : %s", e)
            return None, False

        # Extraction du résultat
        if isinstance(result, tuple):
            success, clicker_id = result
        else:
            success, clicker_id = bool(result), None

        # Retrouve le membre à partir de l'ID
        winner = None
        if clicker_id is not None:
            winner = next((p for p in active_players if p.id == clicker_id), None)

        return winner, bool(success)
