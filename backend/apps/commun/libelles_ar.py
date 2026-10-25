"""Libelles courts (en-tetes de tableaux, statuts, mois...) utilises dans les documents PDF/Excel. Voir traduction.py."""

LIBELLES_AR = {
    # Statuts
    "Valide": "معتمد", "Brouillon": "مسودة", "Present": "حاضر", "Absent": "غائب", "Retard": "متأخر",
    "Abs": "غ", "Abs.J": "غ.ع", "NA": "غ.م", "Actif": "نشط", "Oui": "نعم", "Non": "لا",
    "Admis(e)": "ناجح(ة)", "Redouble": "معيد(ة)", "Exclu(e)": "مفصول(ة)",
    "Non paye": "غير مدفوع", "Partiel": "جزئي", "Paye": "مدفوع", "Paye partiellement": "مدفوع جزئيًا",
    "(provisoire)": "(مؤقت)", "PROVISOIRE": "مؤقت",
    # En-tetes communs
    "Matricule": "الرقم المدرسي", "Nom": "الاسم", "Prenom": "الاسم الشخصي", "Sexe": "الجنس",
    "Etudiants": "التلاميذ", "Notes": "النقاط", "Presences": "الحضور", "Classement": "الترتيب", "Annuel": "سنوي",
    "Annee scolaire": "السنة الدراسية", "Classe": "القسم", "Classe :": "القسم :", "Trimestre": "الفصل",
    "Evaluation": "التقييم", "Bareme": "السلّم", "Matiere": "المادة", "Matiere :": "المادة :",
    "Professeur": "الأستاذ", "Professeur :": "الأستاذ :", "Date": "التاريخ", "Date :": "التاريخ :",
    "Horaire": "التوقيت", "Horaire :": "التوقيت :", "Observations": "ملاحظات", "Observation": "ملاحظة",
    "Emploi": "الجدول", "Pause": "استراحة", "Liste de presence": "قائمة الحضور", "Export": "تصدير", "Liste": "قائمة",
    "Masculin": "ذكر", "Feminin": "أنثى", "Annule": "ملغى", "Annulee": "ملغاة", "En cours": "جارٍ", "Terminee": "منتهية",
    "Livree": "مسلّمة", "Ouverte": "مفتوحة", "Fermee": "مغلقة", "Active": "نشطة", "Transferee": "منقول", "Abandon": "انقطاع",
    "Diplome": "متخرج", "Inactif": "غير نشط", "Planifie": "مبرمجة", "Effectue": "منجزة", "Remplace": "مستبدلة",
    "Publie": "منشور", "Archive": "مؤرشف", "Administrateur": "مدير النظام", "Directeur": "المدير", "Comptable": "المحاسب",
    "Responsable de la scolarite": "مسؤول المصاريف الدراسية", "Responsable pedagogique": "المسؤول البيداغوجي",
    "Au nombre d'heures": "بعدد الساعات", "Salaire fixe": "راتب ثابت",
    "Adresse": "العنوان", "Annee scolaire :": "السنة الدراسية :",
    "N°": "رقم", "Abs.": "غياب", "Ret.": "تأخر", "Mois": "الشهر", "Effectif": "العدد", "Legende": "الرموز", "Note / statut": "النقطة / الحالة",
    # Bulletins
    "Matieres": "المواد", "Moy.": "المعدل", "Coeff": "المعامل", "Rang": "الترتيب", "Total": "المجموع", "TOTAL": "المجموع",
    "T1": "ف1", "T2": "ف2", "T3": "ف3", "Bulletins": "كشوف النقاط",
    "Moy. interrogations": "معدل الاختبارات", "1ere composition": "الامتحان 1", "2e composition": "الامتحان 2",
    "Moyenne generale": "المعدل العام", "Decision": "القرار", "Remarque": "ملاحظة",
    "BULLETIN DE NOTES - 1er TRIMESTRE": "كشف النقاط - الفصل الأول",
    "BULLETIN DE NOTES - 2e TRIMESTRE": "كشف النقاط - الفصل الثاني",
    "BULLETIN DE NOTES - 3e TRIMESTRE": "كشف النقاط - الفصل الثالث",
    "BULLETIN DE NOTES - ANNUEL": "كشف النقاط - السنوي",
    "Moyenne generale : {} / 20*": "المعدل العام : {0} / 20*",
    "Ne(e) le : {}": "تاريخ الميلاد : {0}",
    "Resultats valides": "النتائج معتمدة", "Resultats PROVISOIRES (non valides)": "النتائج مؤقتة (غير معتمدة)",
    # Remuneration
    "Heures": "الساعات", "Brut": "الإجمالي", "Primes": "المكافآت", "Retenues": "الخصومات", "Net": "الصافي",
    "Solde": "الرصيد", "Paiement": "الدفع", "Tarif": "السعر", "Montant": "المبلغ", "Prime": "مكافأة", "Retenue": "خصم",
    "Reference": "المرجع", "Type": "النوع", "Statut du paiement": "حالة الدفع", "Statut du releve": "حالة الكشف",
    "Acompte / paiement partiel": "دفعة مقدمة / دفع جزئي", "Annulation": "إلغاء", "Especes": "نقدًا",
    "Virement": "تحويل بنكي", "Cheque": "شيك", "Paiement mobile": "دفع عبر الهاتف", "UM": "أوقية",
    "Salle {}": "القاعة {0}", "Etat de paiement": "كشف الدفع",
    # Jours et mois
    "Lundi": "الاثنين", "Mardi": "الثلاثاء", "Mercredi": "الأربعاء", "Jeudi": "الخميس", "Vendredi": "الجمعة",
    "Samedi": "السبت", "Dimanche": "الأحد",
    "janvier": "يناير", "fevrier": "فبراير", "mars": "مارس", "avril": "أبريل", "mai": "مايو", "juin": "يونيو",
    "juillet": "يوليو", "aout": "أغسطس", "septembre": "سبتمبر", "octobre": "أكتوبر", "novembre": "نوفمبر",
    "decembre": "ديسمبر",
    # Statuts de notification, canaux
    "En attente": "قيد الانتظار", "Envoye": "مرسل", "Livre": "مسلَّم", "Echec": "فشل",
    "API WhatsApp Business": "واجهة WhatsApp Business", "Lien wa.me (manuel)": "رابط wa.me (يدوي)",
}
