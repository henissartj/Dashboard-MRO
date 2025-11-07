import dash
from dash import dcc, html

dash.register_page(
    __name__,
    path="/epheverisme",
    name="Éphévérisme",
    order=81,
)

EPHEV_MD = r"""
# Théorie de l'Éphévérisme

L’éphévérisme est un néologisme construit pour nommer une posture esthétique et existentielle précise : celle qui érige en principe la fulgurance de l’instant créatif, en refusant de subordonner la valeur d’une œuvre à sa durée, à son accumulation ou à sa conservation. Il se forme à partir d’un déplacement volontaire du radical d’« éphémère » (ce qui ne dure pas) vers « éphévé- », qui évoque aussi l’éphèbe : la jeunesse, l’adolescence spirituelle, l’état d’inachèvement ardent. Ce choix morphologique n’est pas ornemental : il signale une esthétique du commencement intensif plutôt qu’une simple apologie du court terme.

L’éphévérisme désigne ainsi un régime où l’œuvre est investie à son point d’apparition maximale : tout se joue dans l’acte. La valeur se concentre dans le geste initial, dans la combustion de la forme au moment où elle se sépare de son auteur. Une fois l’œuvre déposée dans le monde, l’attachement se défait sans ressentiment : il ne s’agit ni de destruction programmée, ni de mépris de la trace, mais d’un refus de l’enlisement. L’artiste éphévériste accepte de se déprendre de ce qu’il a produit dès l’instant où l’acte créateur a été pleinement accompli. Ce détachement n’annule pas l’intensité ; il en est la conséquence logique. L’œuvre, en ce sens, devient une braise déjà offerte, non un patrimoine à défendre.

Par contraste avec les traditions qui valorisent la monumentalité, la mémoire cumulative ou la promesse d’archive, l’éphévérisme s’oppose à la fixation comme critère de légitimité. Il ne s’inscrit ni dans le romantisme de la blessure conservée, ni dans l’ironie dadaïste, ni dans la réduction conceptuelle, ni dans la seule contemplation méditative de l’impermanence. Il propose une troisième voie : une ascèse du recommencement. Le geste créateur est total, mais son auteur n’y demeure pas. Il se lasse non par fatigue, mais par fidélité à l’exigence d’un nouvel élan. L’instabilité n’est plus un défaut, elle devient condition de la fécondité.

Cette logique affecte aussi le rapport au marché et aux institutions : l’éphévérisme ne construit pas son sens sur la reconnaissance tardive, les circuits de validation ou la pérennisation matérielle. Si l’œuvre subsiste, elle le fait en quelque sorte sans l’auteur, qui a déjà déplacé le foyer de sa responsabilité créatrice. La temporalité propre de ce geste repose sur une séquence organique : concevoir, consumer, délaisser, recommencer. La durée ne légitime plus, c’est l’intensité du commencement qui fait loi.

---

## Définition lexicale

**ÉPHÉVÉRISME** — *subst. masc.*

**I. Formation**

Dérivé néologique à partir du champ d’« éphémère » (du gr. *ephemeros*, « qui ne dure qu’un jour »), modulé par une altération volontaire en *éphév-* intégrant l’écho de l’« éphèbe », puis suffixé en *-isme* (doctrine, courant, posture).

**II. Sens principal**

> Courant poétique, esthétique et existentiel qui érige en principe la fulgurance de l’instant créatif, considérant que la véritable valeur d’une œuvre réside dans l’élan de sa naissance plutôt que dans sa conservation, sa capitalisation ou sa postérité.

L’éphévérisme affirme une tension structurante entre passion et détachement : don absolu dans le moment de création, puis dés-identification rapide à l’objet produit. La mémoire ne repose pas sur l’accumulation des œuvres, mais sur l’intensité des commencements.

**III. Par extension**

> Attitude consistant à vivre et créer dans l’embrasement du présent, en refusant toute fixation identitaire ou matérielle prolongée, sans pour autant sombrer dans le nihilisme ou le pur effacement.

**IV. Dérivés**

- **Éphévériste** : adj. et subst. — qui relève de l’éphévérisme ou s’en réclame.
- **Éphévérique** : adj. — relatif à l’esthétique, à la dynamique ou à l’état d’esprit éphévériste.

---

## Position théorique

L’éphévérisme, dans son articulation au Modèle de Résonance Ontogénétique (MRO), peut se lire comme la version symbolique d’une dynamique où la mémoire ne se forme qu’à travers une légère dissipation : sans perte, pas d’inscription ; sans détachement, pas d’ontogenèse. Il ne s’agit pas de rompre avec la forme, mais de maintenir l’espace du recommencement ouvert. L’œuvre est un point d’intensité, non une clôture.
"""

layout = html.Div(
    style={"maxWidth": "900px", "margin": "0 auto", "padding": "32px"},
    children=[
        dcc.Markdown(EPHEV_MD, link_target="_blank"),
    ],
)