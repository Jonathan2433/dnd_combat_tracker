from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# =====================
# MODELS
# =====================

MONSTER_TEMPLATES = {
    "Gobelin": {
        "type": "Ennemi",
        "hp": 7,
        "ac": 15,
        "initiative": 2
    },
    "Hobgobelin": {
        "type": "Ennemi",
        "hp": 11,
        "ac": 18,
        "initiative": 1
    },
    "Bugbear": {
        "type": "Ennemi",
        "hp": 27,
        "ac": 16,
        "initiative": 2
    },
    "Redbrand Ruffian": {
        "type": "Ennemi",
        "hp": 11,
        "ac": 14,
        "initiative": 1
    },
    "Loup": {
        "type": "Ennemi",
        "hp": 11,
        "ac": 13,
        "initiative": 2
    },
    "Nothic": {
        "type": "Boss",
        "hp": 45,
        "ac": 15,
        "initiative": 3
    },
    "Spectre": {
        "type": "Ennemi",
        "hp": 22,
        "ac": 12,
        "initiative": 2
    },
    "Gelatinous Cube": {
        "type": "Ennemi",
        "hp": 84,
        "ac": 6,
        "initiative": -4
    },
    "Venomfang (Young Green Dragon)": {
        "type": "Boss",
        "hp": 136,
        "ac": 18,
        "initiative": 1
    }
}

CONDITIONS_LIST = [
    "Aveuglé",
    "Charmé",
    "Assourdi",
    "Effrayé",
    "Agrippé",
    "Paralysé",
    "Pétrifié",
    "Empoisonné",
    "À terre",
    "Entravé",
    "Étourdi",
    "Inconscient",
    "Épuisement",
    "Concentration"
]

CONDITIONS_DESCRIPTIONS = {
    "Aveuglé": "Ne voit rien. Échoue automatiquement aux tests basés sur la vue. Attaques contre lui avec avantage ; ses attaques avec désavantage.",
    "Charmé": "Ne peut pas attaquer ou cibler le charmeur avec des effets nuisibles. Le charmeur a avantage aux tests sociaux contre lui.",
    "Assourdi": "N’entend rien. Échoue automatiquement aux tests basés sur l’ouïe.",
    "Effrayé": "Désavantage aux tests et attaques tant que la source est visible. Ne peut pas se rapprocher volontairement de la source.",
    "Agrippé": "Vitesse = 0. Fin si l’agrippeur est neutralisé ou éloigné.",
    "Paralysé": "Incapable d’agir. Échoue aux sauvegardes FOR/DEX. Attaques contre lui avec avantage. Coup critique automatique au contact.",
    "Pétrifié": "Transformé en pierre. Incapable d’agir. Résistance à tous les dégâts. Immunisé poison/maladie.",
    "Empoisonné": "Désavantage aux jets d’attaque et tests de caractéristique.",
    "À terre": "Désavantage aux attaques. Attaques contre lui avec avantage au corps à corps, désavantage à distance.",
    "Entravé": "Vitesse = 0. Désavantage aux attaques et sauvegardes DEX. Attaques contre lui avec avantage.",
    "Étourdi": "Incapable d’agir. Échoue aux sauvegardes FOR/DEX. Attaques contre lui avec avantage.",
    "Inconscient": "Incapable d’agir, tombe à terre. Échoue FOR/DEX. Attaques contre lui avec avantage. Critique auto au contact.",
    "Épuisement": "Applique des pénalités cumulatives selon le niveau d’épuisement.",
    "Concentration": "Si vous subissez des dégâts, vous devez réussir un jet de sauvegarde de Constitution pour maintenir le sort."
}

class Combat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    round = db.Column(db.Integer, default=1)
    current_turn = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_closed = db.Column(db.Boolean, default=False)
    combatants = db.relationship('Combatant', backref='combat', cascade="all, delete")
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    current_turn_start = db.Column(db.DateTime, nullable=True)
    current_round_start = db.Column(db.DateTime, nullable=True)
    has_started = db.Column(db.Boolean, default=False)

class CombatLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    combat_id = db.Column(db.Integer, db.ForeignKey('combat.id'))
    actor_id = db.Column(db.Integer, nullable=True)
    target_id = db.Column(db.Integer, nullable=True)

    action_type = db.Column(db.String(50))  # damage, heal, condition, ac_mod
    value = db.Column(db.Integer, nullable=True)
    detail = db.Column(db.String(255), nullable=True)

    round_number = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    turn_owner_id = db.Column(db.Integer, nullable=True)
    turn_duration = db.Column(db.Float, nullable=True)  # secondes

class Combatant(db.Model):
    @property
    def ac_total(self):
        return self.ac_base + (self.ac_bonus or 0)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    type = db.Column(db.String(50))
    hp_max = db.Column(db.Integer)
    hp_current = db.Column(db.Integer)
    temp_hp = db.Column(db.Integer, default=0)
    initiative = db.Column(db.Integer)
    ac_base = db.Column(db.Integer)
    ac_bonus = db.Column(db.Integer, default=0)
    conditions = db.Column(db.String(255))
    is_dead = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    group_id = db.Column(db.Integer, nullable=True)
    is_group = db.Column(db.Boolean, default=False)
    group_name = db.Column(db.String(100), nullable=True)
    is_hidden = db.Column(db.Boolean, default=False)
    has_fled = db.Column(db.Boolean, default=False)
    combat_id = db.Column(db.Integer, db.ForeignKey('combat.id'))

class CharacterTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    character_class = db.Column(db.String(50))
    level = db.Column(db.Integer)

    hp_max = db.Column(db.Integer)
    ac_base = db.Column(db.Integer)
    initiative_bonus = db.Column(db.Integer)

    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EncounterTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    difficulty = db.Column(db.String(50))  # Easy, Medium, Hard, Deadly

    combatants_json = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# =====================
# UTILS
# =====================

def get_current_actor(combat):
    combatants = sorted(
        [c for c in combat.combatants if not c.is_hidden and not c.has_fled],
        key=lambda x: x.initiative,
        reverse=True
    )

    # Vérification de sécurité
    if not combatants or combat.current_turn >= len(combatants):
        return None  # Aucun acteur valide trouvé

    return combatants[combat.current_turn]

# =====================
# ROUTES
# =====================

@app.route('/')
def index():
    combats = Combat.query.order_by(Combat.created_at.desc()).all()
    return render_template('index.html', combats=combats)


# =====================
# GESTION TEMPLATES
# =====================

@app.route('/templates')
def manage_templates():
    characters = CharacterTemplate.query.all()
    encounters = EncounterTemplate.query.all()

    return render_template(
        'templates_manager.html',
        characters=characters,
        encounters=encounters
    )


@app.route('/template/character/create', methods=['POST'])
def create_character_template():
    template = CharacterTemplate(
        name=request.form['name'],
        character_class=request.form['character_class'],
        level=int(request.form['level']),
        hp_max=int(request.form['hp_max']),
        ac_base=int(request.form['ac_base']),
        initiative_bonus=int(request.form['initiative_bonus']),
        notes=request.form.get('notes', '')
    )

    db.session.add(template)
    db.session.commit()

    return redirect(url_for('manage_templates'))


@app.route('/template/encounter/create', methods=['POST'])
def create_encounter_template():
    import json

    combatants_data = []

    # Récupérer les données depuis le formulaire
    names = request.form.getlist('combatant_name')
    types = request.form.getlist('combatant_type')
    hps = request.form.getlist('combatant_hp')
    acs = request.form.getlist('combatant_ac')
    initiatives = request.form.getlist('combatant_initiative')

    for i in range(len(names)):
        if names[i]:  # si nom non vide
            combatants_data.append({
                'name': names[i],
                'type': types[i],
                'hp_max': int(hps[i]),
                'ac_base': int(acs[i]),
                'initiative': int(initiatives[i])
            })

    template = EncounterTemplate(
        name=request.form['name'],
        description=request.form.get('description', ''),
        difficulty=request.form['difficulty'],
        combatants_json=json.dumps(combatants_data)
    )

    db.session.add(template)
    db.session.commit()

    return redirect(url_for('manage_templates'))

@app.route('/combat/<int:combat_id>/add_character_template', methods=['POST'])
def add_character_template(combat_id):
    template_id = int(request.form['template_id'])
    template = CharacterTemplate.query.get_or_404(template_id)

    combatant = Combatant(
        name=template.name,
        type="PJ",
        hp_max=template.hp_max,
        hp_current=template.hp_max,
        initiative=template.initiative_bonus,
        ac_base=template.ac_base,
        ac_bonus=0,
        conditions=""
    )

    combatant.combat_id = combat_id
    db.session.add(combatant)
    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combat_id))

@app.route('/combat/<int:combat_id>/load_encounter', methods=['POST'])
def load_encounter(combat_id):
    encounter_id = int(request.form['encounter_id'])
    encounter = EncounterTemplate.query.get_or_404(encounter_id)

    import json
    combatants_data = json.loads(encounter.combatants_json)

    for data in combatants_data:
        combatant = Combatant(
            name=data['name'],
            type=data['type'],
            hp_max=data['hp_max'],
            hp_current=data['hp_max'],
            initiative=data['initiative'],
            ac_base=data['ac_base'],
            ac_bonus=0,
            conditions=""
        )

        combatant.combat_id = combat_id
        db.session.add(combatant)

    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combat_id))

@app.route('/template/character/<int:id>/delete', methods=['POST'])
def delete_character_template(id):
    template = CharacterTemplate.query.get_or_404(id)
    db.session.delete(template)
    db.session.commit()
    return redirect(url_for('manage_templates'))

@app.route('/template/encounter/<int:id>/delete', methods=['POST'])
def delete_encounter_template(id):
    template = EncounterTemplate.query.get_or_404(id)
    db.session.delete(template)
    db.session.commit()
    return redirect(url_for('manage_templates'))

@app.route('/templates/export')
def export_templates():
    from flask import jsonify

    characters = CharacterTemplate.query.all()
    encounters = EncounterTemplate.query.all()

    export_data = {
        'characters': [{
            'name': c.name,
            'character_class': c.character_class,
            'level': c.level,
            'hp_max': c.hp_max,
            'ac_base': c.ac_base,
            'initiative_bonus': c.initiative_bonus,
            'notes': c.notes
        } for c in characters],

        'encounters': [{
            'name': e.name,
            'description': e.description,
            'difficulty': e.difficulty,
            'combatants_json': e.combatants_json
        } for e in encounters]
    }

    return jsonify(export_data)

@app.route('/combat/create', methods=['POST'])
def create_combat():
    name = request.form['name']
    combat = Combat(name=name)
    db.session.add(combat)
    db.session.commit()
    return redirect(url_for('view_combat', combat_id=combat.id))

@app.route('/combat/<int:combat_id>/start')
def start_combat(combat_id):

    combat = Combat.query.get_or_404(combat_id)

    if not combat.has_started:
        now = datetime.utcnow()

        combat.has_started = True
        combat.start_time = now
        combat.current_round_start = now
        combat.current_turn_start = now

        db.session.commit()

    return redirect(url_for('view_combat', combat_id=combat.id))

@app.route('/combat/<int:combat_id>')
def view_combat(combat_id):
    combat = Combat.query.get_or_404(combat_id)

    combatants_sorted = sorted(
        [c for c in combat.combatants if not c.is_hidden and not c.has_fled and not c.is_dead],
        key=lambda x: x.initiative,
        reverse=True
    )

    groups = {}
    singles = []

    for c in combatants_sorted:
        if c.is_hidden:
            continue  # ✅ on ignore les masqués

        if c.group_id:
            groups.setdefault(c.group_id, []).append(c)
        else:
            singles.append(c)

    # ✅ NOUVEAU : calcul état visuel des groupes
    group_condition_states = {}

    for group_id, members in groups.items():
        group_condition_states[group_id] = {}

        for condition in CONDITIONS_LIST:
            count = 0
            for m in members:
                if m.conditions and condition in m.conditions.split(","):
                    count += 1

            if count == 0:
                state = "none"
            elif count == len(members):
                state = "all"
            else:
                state = "partial"

            group_condition_states[group_id][condition] = state

    initiative_order = sorted(
        [c for c in combat.combatants if not c.is_hidden],
        key=lambda x: x.initiative,
        reverse=True
    )

    character_templates = CharacterTemplate.query.all()
    encounter_templates = EncounterTemplate.query.all()

    return render_template(
        'combat.html',
        combat=combat,
        groups=groups,
        singles=singles,
        group_condition_states=group_condition_states,
        conditions_list=CONDITIONS_LIST,
        conditions_descriptions=CONDITIONS_DESCRIPTIONS,
        MONSTER_TEMPLATES=MONSTER_TEMPLATES,
        character_templates=character_templates,
        encounter_templates=encounter_templates,
        start_time=combat.start_time,
        round_start=combat.current_round_start,
        turn_start=combat.current_turn_start,
        initiative_order=combatants_sorted,
    )

@app.route('/combat/<int:combat_id>/player')
def view_combat_player(combat_id):

    combat = Combat.query.get_or_404(combat_id)

    combatants_sorted = sorted(
        [c for c in combat.combatants if not c.is_hidden],
        key=lambda x: x.initiative,
        reverse=True
    )

    initiative_order = sorted(
        [c for c in combat.combatants if not c.is_hidden],
        key=lambda x: x.initiative,
        reverse=True
    )

    groups = {}
    singles = []

    for c in combatants_sorted:
        if c.is_hidden:
            continue  # ✅ on ignore les masqués

        if c.group_id:
            groups.setdefault(c.group_id, []).append(c)
        else:
            singles.append(c)

    # ✅ NOUVEAU : calcul état visuel des groupes
    group_condition_states = {}

    for group_id, members in groups.items():
        group_condition_states[group_id] = {}

        for condition in CONDITIONS_LIST:
            count = 0
            for m in members:
                if m.conditions and condition in m.conditions.split(","):
                    count += 1

            if count == 0:
                state = "none"
            elif count == len(members):
                state = "all"
            else:
                state = "partial"

            group_condition_states[group_id][condition] = state

    return render_template(
        'combat_player.html',
        combat=combat,
        combatants=combatants_sorted,
        start_time=combat.start_time,
        round_start=combat.current_round_start,
        turn_start=combat.current_turn_start
    )

@app.route('/combat/<int:combat_id>/add', methods=['POST'])
def add_combatant(combat_id):
    combat = Combat.query.get(combat_id)

    if combat.has_started:
        # On garde le même index mais on revalide qu'il n'est pas hors limite
        combatants = sorted(
            [c for c in combat.combatants if not c.is_hidden],
            key=lambda x: x.initiative,
            reverse=True
        )
        if combat.current_turn >= len(combatants):
            combat.current_turn = 0

    hp_max = int(request.form['hp_max'])
    hp_current = request.form.get('hp_current')
    group_id = db.Column(db.Integer, nullable=True)
    is_group = db.Column(db.Boolean, default=False)
    group_name = db.Column(db.String(100), nullable=True)

    if hp_current and hp_current.strip() != "":
        hp_current = int(hp_current)
    else:
        hp_current = hp_max

    combatant = Combatant(
        name=request.form['name'],
        type=request.form['type'],
        hp_max=hp_max,
        hp_current=hp_current,
        initiative=int(request.form['initiative']),
        ac_base=int(request.form['ac']),
        ac_bonus=0,
        conditions=""
    )

    combatant.combat_id = combat_id
    db.session.add(combatant)
    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combat_id))

@app.route('/combatant/<int:id>/delete', methods=['POST'])
def delete_combatant(id):
    combatant = Combatant.query.get_or_404(id)
    combat_id = combatant.combat_id

    # Optionnel : supprimer aussi les logs liés à ce combattant
    CombatLog.query.filter(
        (CombatLog.actor_id == id) |
        (CombatLog.target_id == id)
    ).delete(synchronize_session=False)

    db.session.delete(combatant)
    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combat_id))

@app.route('/combatant/<int:id>/toggle_visibility')
def toggle_visibility(id):
    combatant = Combatant.query.get_or_404(id)

    combatant.is_hidden = not combatant.is_hidden
    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combatant.combat_id))

@app.route('/combatant/<int:id>/toggle_fled')
def toggle_fled(id):
    combatant = Combatant.query.get_or_404(id)

    combatant.has_fled = not combatant.has_fled

    # Log de l'action
    combat = combatant.combat
    actor = get_current_actor(combat)

    action_detail = "fled" if combatant.has_fled else "returned"

    log = CombatLog(
        combat_id=combat.id,
        actor_id=actor.id if actor else None,
        target_id=combatant.id,
        turn_owner_id=actor.id if actor else None,
        action_type="status",
        detail="fled" if combatant.has_fled else "returned",
        round_number=combat.round
    )

    db.session.add(log)
    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combatant.combat_id))

@app.route('/combat/<int:combat_id>/create_group', methods=['POST'])
def create_group(combat_id):

    ids = request.form.getlist('selected_combatants')

    if len(ids) < 2:
        return redirect(url_for('view_combat', combat_id=combat_id))

    # ✅ Récupérer uniquement les combattants vivants
    combatants = Combatant.query.filter(
        Combatant.id.in_(ids),
        Combatant.is_dead == False
    ).all()

    # ✅ Si moins de 2 vivants → pas de groupe
    if len(combatants) < 2:
        return redirect(url_for('view_combat', combat_id=combat_id))

    group_id = int(datetime.utcnow().timestamp())
    group_name = combatants[0].name.split(" ")[0]

    for c in combatants:
        c.group_id = group_id
        c.group_name = group_name
        c.is_group = True

    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combat_id))

@app.route('/combat/group/<int:group_id>/ungroup')
def ungroup(group_id):

    combatants = Combatant.query.filter_by(group_id=group_id).all()

    for c in combatants:
        c.group_id = None
        c.group_name = None
        c.is_group = False

    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combatants[0].combat_id))

@app.route('/combat/group/<int:group_id>/damage', methods=['POST'])
def damage_group(group_id):

    amount = int(request.form['amount'])
    members = Combatant.query.filter_by(group_id=group_id).all()

    if not members:
        return redirect(url_for('index'))

    combat = members[0].combat
    actor = get_current_actor(combat)

    for c in members:

        c.hp_current -= amount

        if c.hp_current <= 0:
            c.hp_current = 0
            c.is_dead = True

        # ✅ LOG INDIVIDUEL
        log = CombatLog(
            combat_id=combat.id,
            actor_id=actor.id if actor else None,
            target_id=c.id,
            turn_owner_id=actor.id if actor else None,
            action_type="damage",
            value=amount,
            round_number=combat.round
        )

        db.session.add(log)

    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combat.id))

@app.route('/combat/group/<int:group_id>/heal', methods=['POST'])
def heal_group(group_id):

    amount = int(request.form['amount'])
    members = Combatant.query.filter_by(group_id=group_id).all()

    if not members:
        return redirect(url_for('index'))

    combat = members[0].combat
    actor = get_current_actor(combat)

    for c in members:

        c.hp_current += amount

        # Les PV ne peuvent pas dépasser le max
        # (règle officielle Healing)
        if c.hp_current > c.hp_max:
            c.hp_current = c.hp_max

        if c.hp_current > 0:
            c.is_dead = False

        # ✅ LOG INDIVIDUEL
        log = CombatLog(
            combat_id=combat.id,
            actor_id=actor.id if actor else None,
            target_id=c.id,
            turn_owner_id=actor.id if actor else None,
            action_type="heal",
            value=amount,
            round_number=combat.round
        )

        db.session.add(log)

    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combat.id))

@app.route('/combat/group/<int:group_id>/toggle_condition/<condition>')
def toggle_condition_group(group_id, condition):

    members = Combatant.query.filter_by(group_id=group_id).all()

    if not members:
        return redirect(url_for('index'))

    combat = members[0].combat
    actor = get_current_actor(combat)

    for c in members:

        current_conditions = c.conditions.split(",") if c.conditions else []

        if condition in current_conditions:
            current_conditions.remove(condition)
            action_detail = f"remove:{condition}"
        else:
            current_conditions.append(condition)
            action_detail = f"apply:{condition}"

        c.conditions = ",".join(current_conditions)

        # ✅ Log individuel par cible
        log = CombatLog(
            combat_id=combat.id,
            actor_id=actor.id if actor else None,
            target_id=c.id,
            turn_owner_id=actor.id if actor else None,
            action_type="condition",
            detail=action_detail,
            round_number=combat.round
        )

        db.session.add(log)

    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combat.id))

@app.route('/combat/<int:combat_id>/add_template', methods=['POST'])
def add_template(combat_id):
    template_name = request.form['template']
    quantity = int(request.form['quantity'])
    manual_initiative = request.form.get('initiative')

    template = MONSTER_TEMPLATES.get(template_name)

    if template:
        for i in range(quantity):

            # Si initiative manuelle saisie → on l’utilise
            if manual_initiative and manual_initiative.strip() != "":
                initiative_value = int(manual_initiative)
            else:
                initiative_value = template["initiative"]

            combatant = Combatant(
                name=f"{template_name} {i+1}" if quantity > 1 else template_name,
                type=template["type"],
                hp_max=template["hp"],
                hp_current=template["hp"],
                initiative=initiative_value,
                ac_base=template["ac"],
                ac_bonus=0,
                conditions=""
            )

            combatant.combat_id = combat_id
            db.session.add(combatant)

        db.session.commit()

    return redirect(url_for('view_combat', combat_id=combat_id))


@app.route('/combatant/<int:id>/damage', methods=['POST'])
def damage(id):
    combatant = Combatant.query.get_or_404(id)
    amount = int(request.form['amount'])

    # Appliquer d'abord aux PV temporaires
    damage_to_temp = min(combatant.temp_hp, amount)
    combatant.temp_hp -= damage_to_temp

    # Le reste aux PV normaux
    remaining_damage = amount - damage_to_temp
    if remaining_damage > 0:
        combatant.hp_current -= remaining_damage
        if combatant.hp_current <= 0:
            combatant.hp_current = 0
            combatant.is_dead = True

    # Log
    combat = combatant.combat
    actor = get_current_actor(combat)

    log = CombatLog(
        combat_id=combat.id,
        actor_id=actor.id if actor else None,
        target_id=combatant.id,
        turn_owner_id=actor.id if actor else None,
        action_type="damage",
        value=amount,
        round_number=combat.round
    )

    db.session.add(log)
    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combat.id))


    return redirect(url_for('view_combat', combat_id=combatant.combat_id))

@app.route('/combatant/<int:id>/heal', methods=['POST'])
def heal(id):
    combatant = Combatant.query.get_or_404(id)
    amount = int(request.form['amount'])

    combatant.hp_current += amount

    # ✅ Ne pas dépasser le max
    if combatant.hp_current > combatant.hp_max:
        combatant.hp_current = combatant.hp_max

    # ✅ Si le combattant était mort à 0 HP → il revient
    if combatant.hp_current > 0:
        combatant.is_dead = False
    combat = combatant.combat
    actor = get_current_actor(combat)

    log = CombatLog(
        combat_id=combat.id,
        actor_id=actor.id if actor else None,
        target_id=combatant.id,
        turn_owner_id=actor.id if actor else None,
        action_type="heal",
        value=amount,
        round_number=combat.round
    )

    db.session.add(log)

    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combatant.combat_id))

@app.route('/combatant/<int:id>/modify_ac', methods=['POST'])
def modify_ac(id):
    combatant = Combatant.query.get_or_404(id)
    amount = int(request.form['amount'])

    combatant.ac_bonus += amount

    combat = combatant.combat
    actor = get_current_actor(combat)

    log = CombatLog(
        combat_id=combat.id,
        actor_id=actor.id if actor else None,
        target_id=combatant.id,
        turn_owner_id=actor.id if actor else None,
        action_type="ac_mod",
        value=amount,
        round_number=combat.round
    )

    db.session.add(log)
    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combat.id))


@app.route('/combatant/<int:id>/modify_temp_hp', methods=['POST'])
def modify_temp_hp(id):
    combatant = Combatant.query.get_or_404(id)
    amount = int(request.form['amount'])

    # Si nouveau montant supérieur, on remplace
    if amount > combatant.temp_hp:
        combatant.temp_hp = amount

    # Log de l'action
    combat = combatant.combat
    actor = get_current_actor(combat)

    log = CombatLog(
        combat_id=combat.id,
        actor_id=actor.id if actor else None,
        target_id=combatant.id,
        turn_owner_id=actor.id if actor else None,
        action_type="temp_hp",
        value=amount,
        round_number=combat.round
    )

    db.session.add(log)
    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combat.id))

@app.route('/combatant/<int:id>/toggle_condition/<condition>')
def toggle_condition(id, condition):
    combatant = Combatant.query.get_or_404(id)
    combat = combatant.combat

    current_conditions = combatant.conditions.split(",") if combatant.conditions else []

    # Déterminer si on ajoute ou retire
    if condition in current_conditions:
        current_conditions.remove(condition)
        action_detail = f"remove:{condition}"
    else:
        current_conditions.append(condition)
        action_detail = f"apply:{condition}"

    combatant.conditions = ",".join(current_conditions)

    # ✅ Récupérer l'acteur du tour
    actor = get_current_actor(combat)

    # ✅ LOG IMPORTANT
    log = CombatLog(
        combat_id=combat.id,
        actor_id=actor.id if actor else None,
        target_id=combatant.id,
        turn_owner_id=actor.id if actor else None,
        action_type="condition",
        detail=action_detail,
        round_number=combat.round
    )

    db.session.add(log)
    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combat.id))

@app.route('/combat/<int:combat_id>/next_turn')
def next_turn(combat_id):

    combat = Combat.query.get_or_404(combat_id)

    # ✅ Sécurité : ne rien faire si le combat n’a pas commencé
    if not combat.has_started:
        return redirect(url_for('view_combat', combat_id=combat.id))

    now = datetime.utcnow()

    # =========================
    # 1️⃣ CALCUL DURÉE DU TOUR PRÉCÉDENT
    # =========================

    if combat.current_turn_start:

        previous_actor = get_current_actor(combat)

        if previous_actor:
            turn_duration = (now - combat.current_turn_start).total_seconds()

            log = CombatLog(
                combat_id=combat.id,
                actor_id=previous_actor.id,
                turn_owner_id=previous_actor.id,
                action_type="turn_time",
                value=int(turn_duration),
                round_number=combat.round,
                turn_duration=turn_duration
            )

            db.session.add(log)

    # =========================
    # 2️⃣ PASSAGE AU TOUR SUIVANT
    # =========================

    combatants = sorted(
        [c for c in combat.combatants if not c.is_hidden],
        key=lambda x: x.initiative,
        reverse=True
    )

    combat.current_turn += 1

    # =========================
    # 3️⃣ SI FIN DE ROUND
    # =========================

    if combat.current_turn >= len(combatants):

        # ✅ Calcul durée du round
        if combat.current_round_start:
            round_duration = (now - combat.current_round_start).total_seconds()

            log = CombatLog(
                combat_id=combat.id,
                action_type="round_time",
                value=int(round_duration),
                round_number=combat.round
            )

            db.session.add(log)

        # ✅ Reset tour + incrément round
        combat.current_turn = 0
        combat.round += 1

        # ✅ Nouveau round commence maintenant
        combat.current_round_start = now

    # =========================
    # 4️⃣ NOUVEAU TOUR COMMENCE
    # =========================

    combat.current_turn_start = now

    db.session.commit()

    return redirect(url_for('view_combat', combat_id=combat.id))

@app.route('/combat/<int:combat_id>/close')
def close_combat(combat_id):

    combat = Combat.query.get_or_404(combat_id)
    now = datetime.utcnow()

    # ✅ Finaliser dernier tour
    if combat.current_turn_start:
        turn_duration = (now - combat.current_turn_start).total_seconds()

        previous_actor = get_current_actor(combat)

        if previous_actor:
            log = CombatLog(
                combat_id=combat.id,
                actor_id=previous_actor.id,
                turn_owner_id=previous_actor.id,
                action_type="turn_time",
                value=int(turn_duration),
                round_number=combat.round,
                turn_duration=turn_duration
            )
            db.session.add(log)

    # ✅ Finaliser dernier round
    if combat.current_round_start:
        round_duration = (now - combat.current_round_start).total_seconds()

        log = CombatLog(
            combat_id=combat.id,
            action_type="round_time",
            value=int(round_duration),
            round_number=combat.round
        )
        db.session.add(log)

    combat.end_time = now
    combat.is_closed = True

    db.session.commit()

    return redirect(url_for('combat_summary', combat_id=combat.id))

@app.route('/combat/<int:combat_id>/summary')
def combat_summary(combat_id):
    combat = Combat.query.get_or_404(combat_id)
    logs = CombatLog.query.filter_by(
        combat_id=combat_id
    ).order_by(CombatLog.timestamp).all()

    # =========================
    # DURÉE TOTALE DU COMBAT (format MM:SS)
    # =========================

    if combat.start_time and combat.end_time:
        total_seconds = int(
            (combat.end_time - combat.start_time).total_seconds()
        )
        total_duration = f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"
    else:
        total_duration = "00:00"

    total_rounds = combat.round
    total_deaths = len([c for c in combat.combatants if c.is_dead])
    total_fled = len([c for c in combat.combatants if c.has_fled])

    total_damage = sum(
        log.value or 0
        for log in logs
        if log.action_type == "damage"
    )

    total_heal = sum(
        log.value or 0
        for log in logs
        if log.action_type == "heal"
    )
    total_fled = len([c for c in combat.combatants if c.has_fled])

    # =========================
    # TEMPS PAR ROUND (format MM:SS)
    # =========================

    round_times = {}

    for log in logs:
        if log.action_type == "round_time":
            seconds = log.value
            round_times[log.round_number] = f"{seconds // 60:02d}:{seconds % 60:02d}"

    # =========================
    # TEMPS PAR TOUR (format MM:SS)
    # =========================

    combatant_lookup = {c.id: c.name for c in combat.combatants}

    turn_times = {}

    for log in logs:
        if log.action_type == "turn_time":
            seconds = log.value
            formatted_time = f"{seconds // 60:02d}:{seconds % 60:02d}"

            turn_times.setdefault(log.round_number, []).append({
                "actor": combatant_lookup.get(log.turn_owner_id, "Inconnu"),
                "duration": formatted_time
            })

    # =========================
    # STATISTIQUES PAR COMBATTANT
    # =========================

    combatant_stats = []

    for c in combat.combatants:
        damage_done = sum(
            log.value or 0
            for log in logs
            if log.actor_id == c.id and log.action_type == "damage"
        )

        damage_taken = sum(
            log.value or 0
            for log in logs
            if log.target_id == c.id and log.action_type == "damage"
        )

        heal_done = sum(
            log.value or 0
            for log in logs
            if log.actor_id == c.id and log.action_type == "heal"
        )

        heal_taken = sum(
            log.value or 0
            for log in logs
            if log.target_id == c.id and log.action_type == "heal"
        )

        conditions_applied = len([
            log for log in logs
            if log.actor_id == c.id
               and log.action_type == "condition"
               and log.detail.startswith("apply:")
        ])

        conditions_received = len([
            log for log in logs
            if log.target_id == c.id
               and log.action_type == "condition"
               and log.detail.startswith("apply:")
        ])

        ac_bonus_given = sum(
            log.value or 0
            for log in logs
            if log.actor_id == c.id
            and log.action_type == "ac_mod"
        )

        # Temps total formaté en MM:SS
        time_seconds = sum(
            log.value or 0
            for log in logs
            if log.action_type == "turn_time"
            and log.turn_owner_id == c.id
        )

        time_formatted = f"{time_seconds // 60:02d}:{time_seconds % 60:02d}"

        combatant_stats.append({
            "name": c.name,
            "is_dead": c.is_dead,
            "has_fled": c.has_fled,
            "damage_done": damage_done,
            "damage_taken": damage_taken,
            "heal_done": heal_done,
            "heal_taken": heal_taken,
            "conditions_applied": conditions_applied,
            "conditions_received": conditions_received,
            "ac_bonus_given": ac_bonus_given,
            "time_spent": time_formatted
        })

        # =========================
        # TIMELINE STRUCTURÉE
        # =========================

        timeline = {}

        for log in logs:
            if log.action_type in ["round_time", "turn_time"]:
                continue

            round_number = log.round_number
            turn_owner = combatant_lookup.get(log.turn_owner_id, "Inconnu")
            actor = combatant_lookup.get(log.actor_id, "Inconnu")
            target = combatant_lookup.get(log.target_id, "Inconnu")

            timeline.setdefault(round_number, {})
            timeline[round_number].setdefault(turn_owner, [])

            if log.action_type == "damage":
                text = f"{actor} inflige {log.value} dégâts à {target}"

            elif log.action_type == "heal":
                text = f"{actor} soigne {log.value} PV à {target}"

            elif log.action_type == "condition":
                if log.detail.startswith("apply:"):
                    condition = log.detail.split(":")[1]
                    text = f"{actor} applique {condition} à {target}"
                else:
                    condition = log.detail.split(":")[1]
                    text = f"{actor} retire {condition} à {target}"

            elif log.action_type == "ac_mod":
                text = f"{actor} modifie la CA de {target} de {log.value:+d}"

            elif log.action_type == "status":
                if log.detail == "fled":
                    text = f"{target} a pris la fuite"
                elif log.detail == "returned":
                    text = f"{target} est revenu au combat"
                else:
                    text = f"Statut de {target} modifié: {log.detail}"

            else:
                text = "Action inconnue"

            timeline[round_number][turn_owner].append(text)

        return render_template(
            "combat_summary.html",
            combat=combat,
            total_duration=total_duration,
            total_rounds=total_rounds,
            total_deaths=total_deaths,
            total_fled=total_fled,
            total_damage=total_damage,
            total_heal=total_heal,
            combatant_stats=combatant_stats,
            timeline=timeline,
            round_times=round_times,
            turn_times=turn_times
        )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)