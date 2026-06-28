<?xml version="1.0" encoding="UTF-8"?>
<!--
   Validarea mesajului electronic eTransport(fisier XML)
   Schematron version 2.0.2 - Last update: 2024-08-12 
   Schematron version 2.0.1 - Last update: 2022-02-02 
   eTransport RULES version 1.0.1 - Last update: 2022-12-15
   eTransport XSD version 2.01 - Last update: 2022-12-15
   
   See the changes compared to the previous version below 
   v2.0.2:
   - add code XK for Kosovo; for rules BR-CL-001, BR-CL-010
   v2.0.1:
   - eliminate rule BR-047
   - correcting the semantics of the rule BR-020
   - add new rules BR-216, BR-217, BR-218
-->
<schema xmlns="http://purl.oclc.org/dsdl/schematron" queryBinding="xslt2">
  <ns prefix="xs" uri="http://www.w3.org/2001/XMLSchema" />
  <ns prefix="xx" uri="mfp:anaf:dgti:eTransport:declaratie:v2"/>
 
  <phase id="rules_phase">
    <active pattern="Rulesmodel"/>
  </phase>
  
  <phase id="codelist_phase">
    <active pattern="Codesmodel"/>
  </phase>
  
  <phase id="type_phase">
    <active pattern="Typemodel"/>
  </phase>
  <!-- eTransport xml type -->
  <pattern id="Typemodel">
       <rule context="xx:notificare">
      <report test="."
        role="warning"
        flag="warning"
        id="BT-TY-001">
        [BT-TY-001]-Instanta XML este notificare.
      </report>
      <report test="xx:corectie"
        role="warning"
        flag="warning"
        id="BT-TY-002">
        [BT-TY-002]-Instanta XML este corectie.
      </report>
     </rule>
    <rule context="xx:confirmare">
      <report test="."
        role="warning"
        flag="warning"
        id="BT-TY-003">
        [BT-TY-003]-Instanta XML este confirmare.
      </report>
     </rule>
    <rule context="xx:stergere">
      <report test="."
        role="warning"
        flag="warning"
        id="BT-TY-004">
        [BT-TY-004]-Instanta XML este stergere.
      </report>
    </rule> 
    <rule context="xx:modifVehicul"> <!-- v2 -->
      <report test="."
        role="warning"
        flag="warning"
        id="BT-TY-200">
        [BT-TY-200]-Instanta XML este modificare vehicul.
      </report>
    </rule>
    <rule context="xx:eTransport"> <!-- v2 -->
      <assert test="(count(xx:notificare) = 0 and count(xx:stergere) = 0 and count(xx:confirmare) = 0 and count(xx:modifVehicul) = 1)
        or (count(xx:notificare) = 0 and count(xx:stergere) = 0 and count(xx:confirmare) = 1 and count(xx:modifVehicul) = 0)
        or (count(xx:notificare) = 0 and count(xx:stergere) = 1 and count(xx:confirmare) = 0  and count(xx:modifVehicul) = 0)
        or (count(xx:notificare) = 1 and count(xx:stergere) = 0 and count(xx:confirmare) = 0 and count(xx:modifVehicul) = 0)"
        flag="fatal"
        id="BT-TY-005">
        [BT-TY-005]-O instanta eTransport TREBUIE sa aibe cel putin unul si numai unul dintre elementele notificare, confirmare, stergere sau modifVehicul.
      </assert>
    </rule>  
  </pattern>
  
  <!-- Validate eTransport xml according to the  business rules -->
  <pattern id="Rulesmodel">
    <!-- Declaring global variables (in XSLT speak) -->
    <!-- An email address should contain exactly one @ character, which should not be flanked by a space, a period, but at least two characters on either side. A period should not be at the beginning or at the end -->
    <let name="RO-EMAIL-REGEX"  value="'^[0-9a-zA-Z]([0-9a-zA-Z\.]*)[^\.\s@]@[^\.\s@]([0-9a-zA-Z\.]*)[0-9a-zA-Z]$'" />
    <!-- A telephone number should contain at least three digits. -->
    <let name="RO-TELEPHONE-REGEX"  value="'.*([0-9].*){3,}.*'" />
    <!-- EU countries (ISO 3166-1 Codelists)-->
    <let name="ISO-3166-EU-CODES" value="('AT','BE','BG','CZ','CY','DE','DK','EE','EL','ES','FI','HR','HU','IE','IT','FR','LV','LT','LU','MT','NL','PL','PT','RO','SI','SE','SK','XI')"/>
    <!-- Tax Identification Number -->
    <let name="TIN-REGEX"  value="'^(([1-9][0-9]{12})|([1-9][0-9]{1,9}))$'"/>
    <!-- Unique transport identifier -->
    <let name="UIT-REGEX"  value="'[0-9ACDEFHJKLMNPQRTUVWXY]{14}[0-9]{2}'"/>
    <!-- cod tarifar  -->
    <let name="CTR4-REGEX"  value="'^\d{4}$'"/>
    <let name="CTR6-REGEX"  value="'^\d{6}$'"/>
    <let name="CTR8-REGEX"  value="'^\d{8}$'"/>
    <let name="CTR10-REGEX"  value="'^\d{10}$'"/>
    <!-- numeric 12.2  -->
    <let name="NUM12_2-REGEX"  value="'^[0-9]{0,12}(\.[0-9]{0,2})?$'"/>
    <!-- auto  -->
    <let name="AUTO-REGEX"  value="'[0-9A-Z]{2,20}'"/>
    <!-- data modificarii  -->
    <let name="DATEMODIF-REGEX"  value="'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})'"/>
    <let name="STR20-REGEX"  value="'^.{1,20}$'"/>
    <let name="STR30-REGEX"  value="'^.{1,30}$'"/>
    <let name="STR50-REGEX"  value="'^.{1,50}$'"/>
    <let name="STR100-REGEX"  value="'^.{2,100}$'"/>
    <let name="STR200-REGEX"  value="'^.{2,200}$'"/>
 
    <!-- Validate UIT
			3V0P0L0P0T3JUW46
      4C0U0C0J0W3DDQ92
      5Y0Q0L0A0Y3AJA00
      6N0U0A0A0K3PUM07
      7M0L0P0H0K3RAP05
      8H0Q0V0L0Q3WQN41
      9E0P0C0J0J3DQV99
      0C1E0K0N0M3EHP79
      1C1E0Y0Y0N3YLK25
      2D1R0D0L0N3CYH94
      3H1M0A0E0J3FKN75
	   -->	
    <rule context="//@uit">
      <let name="UIT-SUM" value="number(string-to-codepoints(substring(.,1,1))) + number(string-to-codepoints(substring(.,2,1))) + number(string-to-codepoints(substring(.,3,1))) + number(string-to-codepoints(substring(.,4,1))) + number(string-to-codepoints(substring(.,5,1))) + number(string-to-codepoints(substring(.,6,1))) + number(string-to-codepoints(substring(.,7,1))) + number(string-to-codepoints(substring(.,8,1))) + number(string-to-codepoints(substring(.,9,1))) + number(string-to-codepoints(substring(.,10,1))) + number(string-to-codepoints(substring(.,11,1))) + number(string-to-codepoints(substring(.,12,1))) + number(string-to-codepoints(substring(.,13,1))) + number(string-to-codepoints(substring(.,14,1)))"/>
      <let name="UIT-CHECK" value="substring(string($UIT-SUM), (string-length(string($UIT-SUM))-1), 2)"/>
      <assert test="matches(substring(., 15), $UIT-CHECK)"
        flag="fatal"
        id="BR-019" 
        >[BR-019]-Identificatorul unic al transportului (BT-3, BT-52, BT-55 sau BT-56) TREBUIE sa respecte algoritmul de verificare a cifrei de control (<value-of select="name(.)"/> = <value-of select="."/>).   
      </assert>
    </rule>
    
    <!-- Business rules
    changes in v2 compared to the previous version:
      deleted rules: BR-021, BR-022, BR-023, BR-024, BR-044, BR-045, BR-071, BR-072, BR-073, BR-074
      modified rules: BR-004, BR-007, BR-008, BR-031, BR-043, BR-068, BR-069, BR-070
      new rules: BR-201, BR-202, BR-203, BR-204, BR-205, BR-206, BR-207, BR-208, BR-209, BR-210, BR-211, BR-212, BR-213, BR-214, BR-215
    -->  
    <rule context="xx:eTransport">      
      <assert test="matches(normalize-space(@codDeclarant), $TIN-REGEX)"
        flag="fatal"
        id="BR-002"
        >[BR-002]-Codul de identificare fiscala(CUI, CNP, NIF) al declarantului (BT-1) TREBUIE sa aibe un format valid in Romania(RO) (<value-of select="name(@codDeclarant)"/> = <value-of select="@codDeclarant"/>).      
      </assert>
      <assert test="exists(@declPostAvarie) and matches(normalize-space(@declPostAvarie), 'D') or not(exists(@declPostAvarie))" 
        flag="fatal"
        id="BR-201"
        >[BR-201]-Declarare post avarie sistem RO-eTransport poate avea doar valorea 'D' (<value-of select="name(@declPostAvarie)"/> = <value-of select="@declPostAvarie"/>).  <!-- v2 -->    
      </assert>
      
      <assert test="exists(xx:modifVehicul) and xx:modifVehicul/@dataModificare[boolean(normalize-space(.))] or not(exists(xx:modifVehicul))" 
          flag="fatal"
          id="BR-202"
        >[BR-202]-Intr-o instanta eTransport care are elementul modifVehicul, Data modificării vehiculului(BT-64) TREBUIE sa existe. <!-- v2 -->
        </assert>	
      
      <assert test="exists(xx:modifVehicul) and matches(normalize-space(xx:modifVehicul/@dataModificare), $DATEMODIF-REGEX) or not(exists(xx:modifVehicul))"
        flag="fatal"
        id="BR-203"
        >[BR-203]-Data modificării vehiculului(BT-64) TREBUIE sa aibe formatul yyyy-mm-ddThh:mm:ss (<value-of select="name(xx:modifVehicul/@dataModificare)"/> = <value-of select="xx:modifVehicul/@dataModificare"/>). <!-- v2 -->     
      </assert>
      
      <assert test="exists(xx:modifVehicul) and xx:modifVehicul/@nrVehicul[boolean(normalize-space(.))] or not(exists(xx:modifVehicul))" 
        flag="fatal"
        id="BR-204"
        >[BR-204]-Intr-o instanta eTransport care are elementul modifVehicul, Număr înmatriculare vehicul(BT-61) TREBUIE sa existe. <!-- v2 -->
      </assert>	
      
    </rule>
    
    <rule context="//@codTaraOrgTransport">      
      <assert test="((.) = 'RO'  and not(//@codTipOperatiune = '30') and (matches(normalize-space(//@codOrgTransport), $TIN-REGEX))) or not((.) = 'RO' and not(//@codTipOperatiune = '30'))" 
        flag="fatal"
        id="BR-043"
        >[BR-043]-Daca codul tarii organizator transport(BT-21) este 'RO' (Romania) si codul Tip operatiune(BT-4) este diferit de '30' (Transport pe teritoriul national), atunci Cod organizator transpor (CUI, CNP, NIF)(BT-22) TREBUIE sa aiba un format valid in Romania(RO).(<value-of select="name(//@codOrgTransport)"/> = <value-of select="//@codOrgTransport"/>).      
      </assert>
    </rule>
    
    <rule context="//@codTaraOrgTransport">      
      <assert test="((.) = 'RO'  and (//@codTipOperatiune = '30') and ((matches(normalize-space(//@codOrgTransport), $TIN-REGEX)) or matches(normalize-space(//@codOrgTransport), 'PF'))) or not((.) = 'RO' and (//@codTipOperatiune = '30'))" 
        flag="fatal"
        id="BR-209"
        >[BR-209]-Daca codul tarii organizator transport(BT-21) este 'RO' (Romania) si codul Tip operatiune(BT-4) este '30' (Transport pe teritoriul national), atunci Cod organizator transpor (CUI, CNP, NIF)(BT-22) TREBUIE sa aiba un format valid in Romania(RO) sau , in cazul persoanelor fizice române, CNP/NIF poate fi înlocuit cu valoarea 'PF', dacă nu este cunoscut(<value-of select="name(//@codOrgTransport)"/> = <value-of select="//@codOrgTransport"/>).      
      </assert>
    </rule>
    <rule context="xx:notificare/xx:corectie | xx:notificare/xx:notificareAnterioara | xx:stergere | xx:confirmare | xx:modifVehicul"> <!-- v2 -->
      <assert test="@uit[boolean(normalize-space(.))]"
        flag="fatal"
        id="BR-008"
        >[BR-008]-Intr-o instanta eTransport care are unul din elementele corectie, notificareAnterioara, stergere, confirmare sau modifVehicul, Identificatorul unic al transportului TREBUIE sa existe.
      </assert>	
    </rule>
    <rule context="//@uit">
      <assert test="matches(normalize-space(.), $UIT-REGEX)"
        flag="fatal"
        id="BR-003"
        >[BR-003]-Identificatorul unic al transportului TREBUIE sa aibe un format valid (<value-of select="name(.)"/> = <value-of select="."/>).		
      </assert>	
    </rule>
    <rule context="@codTipOperatiune">
      <assert test="(normalize-space(.) = ('10', '12', '14', '20', '22', '24', '60', '70') 
        and normalize-space(//@codTara) = $ISO-3166-EU-CODES 
        and not(normalize-space(//@codTara) = 'RO'))
        or not(normalize-space(.) = ('10', '12', '14', '20', '22', '24', '60', '70'))"
        flag="fatal"
        id="BR-004"
        >[BR-004]-Daca codul operatiunii(BT-4) este 10, 12, 14, 20, 22, 24, 60 sau 70 (Achizitie intracomunitara, Operatiuni in sistem lohn (UE) - intrare, Stocuri la dispozitia clientului (Call-off stock) - intrare, Livrare intracomunitara, Operatiuni in sistem lohn (UE) - iesire, Stocuri la dispozitia clientului (Call-off stock) - iesire, Tranzactie intracomunitara - Intrare pentru depozitare/formare nou transport sau Tranzactie intracomunitara - Iesire dupa depozitare/formare nou transport), atunci codul tarii partenerului comercial (BT-15) TREBUIE sa apartina unei tari din UE. Codul 'RO' este EXCEPTAT (<value-of select='//@codTara'/>).
      </assert>
      <assert test="(normalize-space(.) = ('30') 
        and normalize-space(//@codTara) = 'RO')
        or not(normalize-space(.) = '30')"
        flag="fatal"
        id="BR-005"
        >[BR-005]-Daca codul operatiunii(BT-4) este 30(Transport pe teritoriul national), atunci codul tarii partenerului comercial (BT-15) TREBUIE sa fie corespunzator Romaniei(RO) (<value-of select='//@codTara'/>). 
      </assert>
      <assert test="(normalize-space(.) = ('40','50') 
        and not(normalize-space(//@codTara) = $ISO-3166-EU-CODES))
        or not(normalize-space(.) = ('40','50'))"
        flag="fatal"
        id="BR-006"
        >[BR-006]-Daca codul operatiunii(BT-4) este 40 sau 50(Import sau Export), atunci codul tarii partenerului comercial (BT-15) TREBUIE sa apartina unei tari din afara UE (<value-of select='//@codTara'/>).
      </assert>
      <assert test="((normalize-space(.) = '30' 
        and (matches(normalize-space(//@cod), $TIN-REGEX) or matches(normalize-space(//@cod), 'PF'))))
        or not(normalize-space(.) = '30')"
        flag="fatal"
        id="BR-007"
        >[BR-007]-Daca codul operatiunii(BT-4) este 30(Transport pe teritoriul national), atunci, daca este cunoscut, codul de identificare fiscala al partenerului comercial(BT-16) TREBUIE sa aibe un format valid in Romania(RO) sau, daca acest cod este necunoscut, valoarea 'PF'.  (<value-of select="name(//@cod)"/> = <value-of select="//@cod"/>).
      </assert>
     
      <assert test="(normalize-space(.) = ('30','40','50','60','70') 
        and not(exists(//xx:notificareAnterioara)))
        or not(normalize-space(.) = ('30','40','50','60','70'))"
        flag="fatal"
        id="BR-025"
        >[BR-025]-Daca codul operatiunii(BT-4) este 30, 40, 50, 60 sau 70 (Transport pe teritoriul national, Import, Export, Tranzactie intracomunitara - Intrare pentru depozitare/formare nou transport sau Tranzactie intracomunitara - Iesire dupa depozitare/formare nou transport, atunci notificare aterioara (BG-8) NU TREBUIE sa existe (<value-of select="name(.)"/> = <value-of select="."/>) .
      </assert>
      
      <assert test="(normalize-space(.) = ('20', '22', '24', '30', '50', '70') 
        and not(exists(//xx:locStartTraseuRutier/@codPtf)))
        or not(normalize-space(.) = ('20', '22', '24', '30', '50', '70'))"
        flag="fatal"
        id="BR-212"
        >[BR-212]-Daca codul operatiunii(BT-4) este 20, 22, 24, 30, 50 sau 70 (Livrare intracomunitară, Operaţiuni în sistem lohn (UE) - ieşire, Stocuri la dispoziţia clientului (Call-off stock) - ieşire, Transport pe teritoriul naţional, Export sau Tranzacţie intracomunitară - Ieşire după depozitare/formare nou transport, atunci Codul punctului de trecere frontieră(BT-25), din Locul de start al traseului rutier(BG-6), NU TREBUIE sa existe (<value-of select="name(.)"/> = <value-of select="."/>) .
      </assert>
      <assert test="(normalize-space(.) = ('12', '14', '30', '40', '60') 
        and not(exists(//xx:locFinalTraseuRutier/@codPtf)))
        or not(normalize-space(.) = ('12', '14', '30', '40', '60'))"
        flag="fatal"
        id="BR-213"
        >[BR-213]-Daca codul operatiunii(BT-4) este 12, 14, 30, 40 sau 60 (Operatiuni in sistem lohn (UE) - intrare, Stocuri la dispozitia clientului (Call-off stock) - intrare, Transport pe teritoriul national, Import sau Tranzactie intracomunitara - Intrare pentru depozitare/formare nou transport, atunci Codul punctului de trecere frontieră(BT-37), din Locul de final al traseului rutier(BG-8), NU TREBUIE sa existe (<value-of select="name(.)"/> = <value-of select="."/>) .
      </assert>
    
      <assert test="(normalize-space(.) = ('10','20','30','60','70') 
        and not(exists(//@codBirouVamal)))
        or not(normalize-space(.) = ('10','20','30','60','70'))"
        flag="fatal"
        id="BR-046"
        >[BR-046]-Daca codul operatiunii(BT-4) este 10, 20, 30, 60 sau 70 (Achizitie intracomunitara, Livrare intracomunitara, Transport pe teritoriul national, Tranzactie intracomunitara - Intrare pentru depozitare/formare nou transport sau Tranzactie intracomunitara - Iesire dupa depozitare/formare nou transport), atunci Codul biroului vamal(BT-24) NU TREBUIE sa existe (<value-of select="name(.)"/> = <value-of select="."/>) .
      </assert>
      <!-- v2.0.1
      <assert test="(normalize-space(.) = ('40','50') 
        and exists(//@codBirouVamal))
        or not(normalize-space(.) = ('40','50'))"
        flag="fatal"
        id="BR-047"
        >[BR-047]-Daca codul operatiunii(BT-4) este 40 sau 50 (Export sau Import), atunci Codul biroului vamal(BT-24) TREBUIE sa existe (<value-of select="name(.)"/> = <value-of select="."/>) .
      </assert>  
       -->
    </rule>
    <!-- repetitive -->
    <rule context = "xx:bunuriTransportate">
      
      <assert  
        id="BR-218" 
        flag="fatal" 
        test="exists(@greutateBruta) and @greutateBruta != ''"> <!-- v2.0.1 -->
        [BR-218]-Intr-o Notificare(BG-1), elementul Bunuri transportate(BG-3) trebuie sa contina atributul Greutate bruta (BT-12).
      </assert>
      
      <assert test="(exists(@greutateNeta)
        and (xs:decimal(@greutateBruta) &gt;= xs:decimal(@greutateNeta)))
        or not (exists(@greutateNeta))"
        flag="fatal"
        id="BR-020"
        ><!-- v2.0.1 -->
        [BR-020]-Greutatea bruta(BT-12) TREBUIE sa fie mai mare sau egala cu greutatea neta(BT-11) (<value-of select="name(@greutateBruta)"/> = <value-of select="@greutateBruta"/> &lt; <value-of select="name(@greutateNeta)"/> = <value-of select="@greutateNeta"/> ).       
      </assert>
      <assert test="(normalize-space(@codScopOperatiune) = ('101', '201', '301', '401', '501', '601', '703', '801', '802', '901', '1001', '1101', '9901') 
        and normalize-space(//@codTipOperatiune) =('10'))
        or not(normalize-space(//@codTipOperatiune) = ('10'))"
        flag="fatal"
        id="BR-068"
        >[BR-068]-Daca codul operatiunii(BT-4) este 10(Achizitie intracomunitara), atunci Scopul operatiunii(BT-8) TREBUIE sa ia una dintre valorile: '101', '201', '301', '401', '501', '601', '703', '801', '802', '901', '1001',  '1101', '9901' (<value-of select="name(//@codTipOperatiune)"/> = <value-of select="//@codTipOperatiune"/>  <value-of select="name(@codScopOperatiune)"/> = <value-of select="@codScopOperatiune"/>) .
      </assert>
      
      <assert test="(normalize-space(@codScopOperatiune) = ('101', '301', '703', '801', '802', '9901') 
        and normalize-space(//@codTipOperatiune) =('20'))
        or not(normalize-space(//@codTipOperatiune) = ('20'))"
        flag="fatal"
        id="BR-069"
        >[BR-069]-Daca codul operatiunii(BT-4) este 20(Livrare intracomunitara), atunci Scopul operatiunii(BT-8) TREBUIE sa ia una dintre valorile: '101', '301', '703', '801', '802', '9901' (<value-of select="name(//@codTipOperatiune)"/> = <value-of select="//@codTipOperatiune"/>  <value-of select="name(@codScopOperatiune)"/> = <value-of select="@codScopOperatiune"/>) .
      </assert>
      
      <assert test="(normalize-space(@codScopOperatiune) = ('101', '704', '705', '9901') 
        and normalize-space(//@codTipOperatiune) =('30'))
        or not(normalize-space(//@codTipOperatiune) = ('30'))"
        flag="fatal"
        id="BR-070"
        >[BR-070]-Daca codul operatiunii(BT-4) este 30(Transport pe teritoriul national), atunci Scopul operatiunii(BT-8) TREBUIE sa ia una dintre valorile: '101', '704', '705', '9901' (<value-of select="name(//@codTipOperatiune)"/> = <value-of select="//@codTipOperatiune"/>  <value-of select="name(@codScopOperatiune)"/> = <value-of select="@codScopOperatiune"/>) .
      </assert> 
      
      <assert test="(normalize-space(@codScopOperatiune) = ('9999') 
        and normalize-space(//@codTipOperatiune) =('12', '14', '22', '24', '40', '50', '60', '70'))
        or not(normalize-space(//@codTipOperatiune) = ('12', '14', '22', '24', '40', '50', '60', '70'))"
        flag="fatal"
        id="BR-205"
        >[BR-205]-Daca codul operatiunii(BT-4) este 12(Operatiuni in sistem lohn (UE) - intrare), 14(Stocuri la dispozitia clientului (Call-off stock) - intrare), 22(Operatiuni in sistem lohn (UE) - iesire), 24(Stocuri la dispozitia clientului (Call-off stock) - iesire), 40(Import), 50(Export), 60(Tranzactie intracomunitara - Intrare pentru depozitare/formare nou transport) sau 70(Tranzactie intracomunitara - Iesire dupa depozitare/formare nou transport), atunci Scopul operatiunii(BT-8) TREBUIE sa ia valorea: '9999' (<value-of select="name(//@codTipOperatiune)"/> = <value-of select="//@codTipOperatiune"/>  <value-of select="name(@codScopOperatiune)"/> = <value-of select="@codScopOperatiune"/>) .
      </assert>
      
      <assert test="(exists(@codTarifar)
        and not(normalize-space(//@codTipOperatiune) =('60', '70'))
        or normalize-space(//@codTipOperatiune) = ('60', '70'))"
        flag="fatal"
        id="BR-206"
        >[BR-206]-Daca codul operatiunii(BT-4) este diferit de 60(Tranzactie intracomunitara - Intrare pentru depozitare/formare nou transport) sau 70(Tranzactie intracomunitara - Iesire dupa depozitare/formare nou transport), atunci Cod tarifar(BT-6) TREBUIE sa existe (<value-of select="name(//@codTipOperatiune)"/> = <value-of select="//@codTipOperatiune"/>  <value-of select="name(@codScopOperatiune)"/> = <value-of select="@codScopOperatiune"/>) .
      </assert>
      
      <assert test="(exists(@greutateNeta)
        and not(normalize-space(//@codTipOperatiune) =('60', '70'))
        or normalize-space(//@codTipOperatiune) = ('60', '70'))"
        flag="fatal"
        id="BR-207"
        >[BR-207]-Daca codul operatiunii(BT-4) este diferit de 60(Tranzactie intracomunitara - Intrare pentru depozitare/formare nou transport) sau 70(Tranzactie intracomunitara - Iesire dupa depozitare/formare nou transport), atunci Greutate neta(BT-11) TREBUIE sa existe (<value-of select="name(//@codTipOperatiune)"/> = <value-of select="//@codTipOperatiune"/>) .
      </assert>
      
      <assert test="(exists(@valoareLeiFaraTva)
        and not(normalize-space(//@codTipOperatiune) =('60', '70'))
        or normalize-space(//@codTipOperatiune) = ('60', '70'))"
        flag="fatal"
        id="BR-208"
        >[BR-208]-Daca codul operatiunii(BT-4) este diferit de 60(Tranzactie intracomunitara - Intrare pentru depozitare/formare nou transport) sau 70(Tranzactie intracomunitara - Iesire dupa depozitare/formare nou transport), atunci Valoare fara TVA(BT-13) TREBUIE sa existe (<value-of select="name(//@codTipOperatiune)"/> = <value-of select="//@codTipOperatiune"/>) .
      </assert>
      
    </rule>
    
    <rule context="//@tipDocument">
      <assert test="(normalize-space(.)='9999' and normalize-space(//@observatii))
        or not(normalize-space(.)='9999')"
        flag="fatal"
        id="BR-026"
        >[BR-026]-Daca codul tipului de document este '9999'(Altele), atunci atributul 'observatii' TREBUIE sa existe.      
      </assert>
    </rule>
 

    <rule context="//@cantitate">
      <assert test="xs:decimal(.) > 0"
        id="BR-027" 
        flag="fatal" 
        >[BR-027]-Cantitatea bunului transportat(BT-9) NU TREBUIE sa ia valori negative.
      </assert>
      <assert test="string-length(substring-after(.,'.'))&lt;=2"
        id="BR-035" 
        flag="fatal" 
        >[BR-035]-Cantitatea bunului transportat(BT-9) TREBUIE sa aibe maxim 2 zecimale.
      </assert>
      <assert test="string-length(substring-before(.,'.'))&lt;=12"
        id="BR-036" 
        flag="fatal" 
        >[BR-036]-Cantitatea bunului transportat(BT-9) TREBUIE sa aibe maxim 12 unitati intregi.
      </assert>
    </rule>
    <rule context="//@greutateNeta">
      <assert test="xs:decimal(.) > 0"
        id="BR-028" 
        flag="fatal" 
        >[BR-028]-Greutatea neta a bunului transportat(BT-11) TREBUIE sa fie strict mai mare decat 0(zero).
      </assert>
      <assert test="string-length(substring-after(.,'.'))&lt;=2"
        id="BR-037" 
        flag="fatal" 
        >[BR-037]-Greutatea neta a bunului transportat(BT-11) TREBUIE sa aibe maxim 2 zecimale.
      </assert>
      <assert test="string-length(substring-before(.,'.'))&lt;=12"
        id="BR-038" 
        flag="fatal" 
        >[BR-038]-Greutatea neta a bunului transportat(BT-11) TREBUIE sa aibe maxim 12 unitati intregi.
      </assert>
    </rule>
    <rule context="//@greutateBruta">    
      <assert test="xs:decimal(.) > 0"
        id="BR-029" 
        flag="fatal" 
        >[BR-029]-Greutatea bruta a bunului transportat(BT-12) TREBUIE sa fie strict mai mare decat 0(zero).
      </assert>
      <assert test="string-length(substring-after(.,'.'))&lt;=2"
        id="BR-039" 
        flag="fatal" 
        >[BR-039]-Greutatea bruta a bunului transportat(BT-12) TREBUIE sa aibe maxim 2 zecimale.
      </assert>
      <assert test="string-length(substring-before(.,'.'))&lt;=12"
        id="BR-040" 
        flag="fatal" 
        >[BR-040]-Greutatea bruta a bunului transportat(BT-12) TREBUIE sa aibe maxim 12 unitati intregi.
      </assert>
    </rule>
    <rule context="//@valoareLeiFaraTva">
      <assert test="xs:decimal(.) >= 0"
        id="BR-030" 
        flag="fatal" 
        >[BR-030]-Valoarea bunului transportat(BT-13) NU TREBUIE sa ia valori negative. Valoarea 0(zero) este acceptata.
      </assert>
      <assert test="string-length(substring-after(.,'.'))&lt;=2"
        id="BR-041" 
        flag="fatal" 
        >[BR-041]-Valoarea bunului transportat(BT-13) TREBUIE sa aibe maxim 2 zecimale.
      </assert>
      <assert test="string-length(substring-before(.,'.'))&lt;=12"
        id="BR-042" 
        flag="fatal" 
        >[BR-042]-Valoarea bunului transportat(BT-13) TREBUIE sa aibe maxim 12 unitati intregi.
      </assert>
    </rule>
    <rule context="//@nrVehicul">
      <assert test="matches(normalize-space(.), $AUTO-REGEX)"
        id="BR-031" 
        flag="fatal" 
        >[BR-031]-Numar inmatriculare vehicul(BT-18, BT-61) TREBUIE sa aiba minim 2 caractere si maxim 20 de caractere. Sunt acceptate caractere alfabetice majuscule (A-Z) si caractere numerice(0-9).
      </assert>
    </rule>
    <rule context="//@nrRemorca1">
      <assert test="matches(normalize-space(.), $AUTO-REGEX)"
        id="BR-032" 
        flag="fatal" 
        >[BR-032]-Numar inmatriculare remorca 1(BT-19, BT-62) TREBUIE sa aiba minim 2 caractere si maxim 20 de caractere. Sunt acceptate caractere alfabetice majuscule (A-Z) si caractere numerice(0-9).
      </assert>
    </rule>
    <rule context="//@nrRemorca2">
      <assert test="matches(normalize-space(.), $AUTO-REGEX)"
        id="BR-033" 
        flag="fatal" 
        >[BR-033]-Numar inmatriculare remorca 2(BT-20, BT-63) TREBUIE sa aiba minim 2 caractere si maxim 20 de caractere. Sunt acceptate caractere alfabetice majuscule (A-Z) si caractere numerice(0-9).
      </assert>
    </rule>
    
    <rule context="//@codTarifar">
      <assert test="matches(normalize-space(.), $CTR4-REGEX) or matches(normalize-space(.), $CTR6-REGEX) or matches(normalize-space(.), $CTR8-REGEX)"
        id="BR-034" 
        flag="fatal" 
        >[BR-034]-Codul tarifar(BT-6) TREBUIE sa aibe 4,6 sau 8 caractere. Sunt acceptat doar caractere numerice(0-9).
      </assert>
    </rule>
    
    <rule context="//@denumireLocalitate">
      <assert test="matches(normalize-space(.), $STR100-REGEX)"
        id="BR-214" 
        flag="fatal" 
        >[BR-214]-Denumire localitate(BT-28, BT-40) TREBUIE sa aiba minim 2 caractere si maxim 100 de caractere.
      </assert>
    </rule>
    
    <rule context="//@denumireStrada">
      <assert test="matches(normalize-space(.), $STR100-REGEX)"
        id="BR-215" 
        flag="fatal" 
        >[BR-215]-Denumire strada(BT-29, BT-41) TREBUIE sa aiba minim 2 caractere si maxim 100 de caractere.
      </assert>
    </rule>
    
    <rule context="//xx:locStartTraseuRutier"> <!-- v2 -->
      <assert test="(exists(./@codBirouVamal) and not(exists(./xx:locatie))and not(exists(./@codPtf)))
        or (not(exists(./@codBirouVamal)) and exists(./xx:locatie) and not(exists(./@codPtf)))
        or (not(exists(./@codBirouVamal)) and not(exists(./xx:locatie)) and exists(./@codPtf))"
        flag="fatal"
        id="BR-210">
        [BR-210]-Locul de start al traseului rutier (BG-6) TREBUIE sa aibe cel putin unul si numai unul dintre atributele cod punct de trecere frontiera(BT-25), cod birou vamal(BT-26) sau elementul locatie(BG-7).
      </assert>
      
      <assert test="not((exists(./@codBirouVamal) and not(//@codTipOperatiune = '40')))"> <!-- v2.0.1 -->
        flag="fatal"
        id="BR-216">
        [BR-216]- Daca codul operatiunii este diferit de 40(Import), atunci cod birou vamal(BT-26) din Locul de start al traseului rutier(BG-6) nu trebuie sa existe.
      </assert>
      
    </rule> 

    <rule context="//xx:locFinalTraseuRutier"> <!-- v2 -->
    <assert test="(exists(./@codBirouVamal) and not(exists(./xx:locatie))and not(exists(./@codPtf)))
      or (not(exists(./@codBirouVamal)) and exists(./xx:locatie) and not(exists(./@codPtf)))
      or (not(exists(./@codBirouVamal)) and not(exists(./xx:locatie)) and exists(./@codPtf))"
      flag="fatal"
      id="BR-211">
      [BR-211]-Locul de final al traseului rutier (BG-8) TREBUIE sa aibe cel putin unul si numai unul dintre atributele cod punct de trecere frontiera(BT-37), cod birou vamal(BT-38) sau elementul locatie(BG-9).
    </assert>
      
      <assert test="not((exists(./@codBirouVamal) and not(//@codTipOperatiune = '50')))"> <!-- v2.0.1 -->
        flag="fatal"
        id="BR-217">
        [BR-217]- Daca codul operatiunii este diferit de 50(Export), atunci cod birou vamal(BT-38)din Locul de final al traseului rutier(BG-8) nu trebuie sa existe.
      </assert>
  </rule> 
    
  </pattern> 
 

  <!-- Validate code lits
  changes in v2 compared to the previous version:
    @codTipOperatiune add values 12, 14, 22, 24
    @codScopOperatiune replace all values with new values 101 201 301 401 501 601 703 704 705 801 802 901 1001 1101 9901 9999
  -->
  <pattern id="Codesmodel">
    <rule context="//@codTara">
      <assert
        test="((not(contains(normalize-space(.), ' ')) and contains(' AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH EL ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS XI XK YE YT ZA ZM ZW ', concat(' ', normalize-space(.), ' '))))" 
        id="BR-CL-001"
        flag="fatal"
        >[BR-CL-001]-Codul țării(BT-15) TREBUIE să fie ales din lista de coduri ISO 3166-1. Pentru Grecia TREBUIE uilizat codul "EL".(<name/> = '<value-of select="."/>')</assert>
    </rule>
    <rule context="//@codTaraOrgTransport">
      <assert
        test="((not(contains(normalize-space(.), ' ')) and contains(' AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH EL ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS XI XK YE YT ZA ZM ZW ', concat(' ', normalize-space(.), ' '))))" 
        id="BR-CL-010"
        flag="fatal"
        >[BR-CL-010]-Codul țării transportatorului(BT-22) TREBUIE să fie ales din lista de coduri ISO 3166-1. Pentru Grecia TREBUIE uilizat codul "EL".(<name/> = '<value-of select="."/>')</assert>
    </rule>
    <rule context="//@codJudet">
      <assert
        test="((not(contains(normalize-space(.), ' ')) and contains(' 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 51 52 ', concat(' ', normalize-space(.), ' '))))" 
        id="BR-CL-002"
        flag="fatal"
        >[BR-CL-002]-Codul județului(BT-27/ BT-37) TREBUIE să fie ales din lista de coduri listJudet.(<name/> = '<value-of select="."/>')</assert>
    </rule>
    <rule context="//@codUnitateMasura">
      <assert
        test="((not(contains(normalize-space(.), ' ')) and contains(' 10 11 13 14 15 20 21 22 23 24 25 27 28 33 34 35 37 38 40 41 56 57 58 59 60 61 74 77 80 81 85 87 89 91 1I 2A 2B 2C 2G 2H 2I 2J 2K 2L 2M 2N 2P 2Q 2R 2U 2X 2Y 2Z 3B 3C 4C 4G 4H 4K 4L 4M 4N 4O 4P 4Q 4R 4T 4U 4W 4X 5A 5B 5E 5J A10 A11 A12 A13 A14 A15 A16 A17 A18 A19 A2 A20 A21 A22 A23 A24 A26 A27 A28 A29 A3 A30 A31 A32 A33 A34 A35 A36 A37 A38 A39 A4 A40 A41 A42 A43 A44 A45 A47 A48 A49 A5 A53 A54 A55 A56 A59 A6 A68 A69 A7 A70 A71 A73 A74 A75 A76 A8 A84 A85 A86 A87 A88 A89 A9 A90 A91 A93 A94 A95 A96 A97 A98 A99 AA AB ACR ACT AD AE AH AI AK AL AMH AMP ANN APZ AQ AS ASM ASU ATM AWG AY AZ B1 B10 B11 B12 B13 B14 B15 B16 B17 B18 B19 B20 B21 B22 B23 B24 B25 B26 B27 B28 B29 B3 B30 B31 B32 B33 B34 B35 B4 B41 B42 B43 B44 B45 B46 B47 B48 B49 B50 B52 B53 B54 B55 B56 B57 B58 B59 B60 B61 B62 B63 B64 B66 B67 B68 B69 B7 B70 B71 B72 B73 B74 B75 B76 B77 B78 B79 B8 B80 B81 B82 B83 B84 B85 B86 B87 B88 B89 B90 B91 B92 B93 B94 B95 B96 B97 B98 B99 BAR BB BFT BHP BIL BLD BLL BP BPM BQL BTU BUA BUI C0 C10 C11 C12 C13 C14 C15 C16 C17 C18 C19 C20 C21 C22 C23 C24 C25 C26 C27 C28 C29 C3 C30 C31 C32 C33 C34 C35 C36 C37 C38 C39 C40 C41 C42 C43 C44 C45 C46 C47 C48 C49 C50 C51 C52 C53 C54 C55 C56 C57 C58 C59 C60 C61 C62 C63 C64 C65 C66 C67 C68 C69 C7 C70 C71 C72 C73 C74 C75 C76 C78 C79 C8 C80 C81 C82 C83 C84 C85 C86 C87 C88 C89 C9 C90 C91 C92 C93 C94 C95 C96 C97 C99 CCT CDL CEL CEN CG CGM CKG CLF CLT CMK CMQ CMT CNP CNT COU CTG CTM CTN CUR CWA CWI D03 D04 D1 D10 D11 D12 D13 D15 D16 D17 D18 D19 D2 D20 D21 D22 D23 D24 D25 D26 D27 D29 D30 D31 D32 D33 D34 D36 D41 D42 D43 D44 D45 D46 D47 D48 D49 D5 D50 D51 D52 D53 D54 D55 D56 D57 D58 D59 D6 D60 D61 D62 D63 D65 D68 D69 D73 D74 D77 D78 D80 D81 D82 D83 D85 D86 D87 D88 D89 D91 D93 D94 D95 DAA DAD DAY DB DBM DBW DD DEC DG DJ DLT DMA DMK DMO DMQ DMT DN DPC DPR DPT DRA DRI DRL DT DTN DWT DZN DZP E01 E07 E08 E09 E10 E12 E14 E15 E16 E17 E18 E19 E20 E21 E22 E23 E25 E27 E28 E30 E31 E32 E33 E34 E35 E36 E37 E38 E39 E4 E40 E41 E42 E43 E44 E45 E46 E47 E48 E49 E50 E51 E52 E53 E54 E55 E56 E57 E58 E59 E60 E61 E62 E63 E64 E65 E66 E67 E68 E69 E70 E71 E72 E73 E74 E75 E76 E77 E78 E79 E80 E81 E82 E83 E84 E85 E86 E87 E88 E89 E90 E91 E92 E93 E94 E95 E96 E97 E98 E99 EA EB EQ F01 F02 F03 F04 F05 F06 F07 F08 F10 F11 F12 F13 F14 F15 F16 F17 F18 F19 F20 F21 F22 F23 F24 F25 F26 F27 F28 F29 F30 F31 F32 F33 F34 F35 F36 F37 F38 F39 F40 F41 F42 F43 F44 F45 F46 F47 F48 F49 F50 F51 F52 F53 F54 F55 F56 F57 F58 F59 F60 F61 F62 F63 F64 F65 F66 F67 F68 F69 F70 F71 F72 F73 F74 F75 F76 F77 F78 F79 F80 F81 F82 F83 F84 F85 F86 F87 F88 F89 F90 F91 F92 F93 F94 F95 F96 F97 F98 F99 FAH FAR FBM FC FF FH FIT FL FNU FOT FP FR FS FTK FTQ G01 G04 G05 G06 G08 G09 G10 G11 G12 G13 G14 G15 G16 G17 G18 G19 G2 G20 G21 G23 G24 G25 G26 G27 G28 G29 G3 G30 G31 G32 G33 G34 G35 G36 G37 G38 G39 G40 G41 G42 G43 G44 G45 G46 G47 G48 G49 G50 G51 G52 G53 G54 G55 G56 G57 G58 G59 G60 G61 G62 G63 G64 G65 G66 G67 G68 G69 G70 G71 G72 G73 G74 G75 G76 G77 G78 G79 G80 G81 G82 G83 G84 G85 G86 G87 G88 G89 G90 G91 G92 G93 G94 G95 G96 G97 G98 G99 GB GBQ GDW GE GF GFI GGR GIA GIC GII GIP GJ GL GLD GLI GLL GM GO GP GQ GRM GRN GRO GV GWH H03 H04 H05 H06 H07 H08 H09 H10 H11 H12 H13 H14 H15 H16 H18 H19 H20 H21 H22 H23 H24 H25 H26 H27 H28 H29 H30 H31 H32 H33 H34 H35 H36 H37 H38 H39 H40 H41 H42 H43 H44 H45 H46 H47 H48 H49 H50 H51 H52 H53 H54 H55 H56 H57 H58 H59 H60 H61 H62 H63 H64 H65 H66 H67 H68 H69 H70 H71 H72 H73 H74 H75 H76 H77 H79 H80 H81 H82 H83 H84 H85 H87 H88 H89 H90 H91 H92 H93 H94 H95 H96 H98 H99 HA HAD HBA HBX HC HDW HEA HGM HH HIU HKM HLT HM HMO HMQ HMT HPA HTZ HUR HWE IA IE INH INK INQ ISD IU IUG IV J10 J12 J13 J14 J15 J16 J17 J18 J19 J2 J20 J21 J22 J23 J24 J25 J26 J27 J28 J29 J30 J31 J32 J33 J34 J35 J36 J38 J39 J40 J41 J42 J43 J44 J45 J46 J47 J48 J49 J50 J51 J52 J53 J54 J55 J56 J57 J58 J59 J60 J61 J62 J63 J64 J65 J66 J67 J68 J69 J70 J71 J72 J73 J74 J75 J76 J78 J79 J81 J82 J83 J84 J85 J87 J90 J91 J92 J93 J95 J96 J97 J98 J99 JE JK JM JNT JOU JPS JWL K1 K10 K11 K12 K13 K14 K15 K16 K17 K18 K19 K2 K20 K21 K22 K23 K26 K27 K28 K3 K30 K31 K32 K33 K34 K35 K36 K37 K38 K39 K40 K41 K42 K43 K45 K46 K47 K48 K49 K50 K51 K52 K53 K54 K55 K58 K59 K6 K60 K61 K62 K63 K64 K65 K66 K67 K68 K69 K70 K71 K73 K74 K75 K76 K77 K78 K79 K80 K81 K82 K83 K84 K85 K86 K87 K88 K89 K90 K91 K92 K93 K94 K95 K96 K97 K98 K99 KA KAT KB KBA KCC KDW KEL KGM KGS KHY KHZ KI KIC KIP KJ KJO KL KLK KLX KMA KMH KMK KMQ KMT KNI KNM KNS KNT KO KPA KPH KPO KPP KR KSD KSH KT KTN KUR KVA KVR KVT KW KWH KWN KWO KWS KWT KWY KX L10 L11 L12 L13 L14 L15 L16 L17 L18 L19 L2 L20 L21 L23 L24 L25 L26 L27 L28 L29 L30 L31 L32 L33 L34 L35 L36 L37 L38 L39 L40 L41 L42 L43 L44 L45 L46 L47 L48 L49 L50 L51 L52 L53 L54 L55 L56 L57 L58 L59 L60 L63 L64 L65 L66 L67 L68 L69 L70 L71 L72 L73 L74 L75 L76 L77 L78 L79 L80 L81 L82 L83 L84 L85 L86 L87 L88 L89 L90 L91 L92 L93 L94 L95 L96 L98 L99 LA LAC LBR LBT LD LEF LF LH LK LM LN LO LP LPA LR LS LTN LTR LUB LUM LUX LY M1 M10 M11 M12 M13 M14 M15 M16 M17 M18 M19 M20 M21 M22 M23 M24 M25 M26 M27 M29 M30 M31 M32 M33 M34 M35 M36 M37 M38 M39 M4 M40 M41 M42 M43 M44 M45 M46 M47 M48 M49 M5 M50 M51 M52 M53 M55 M56 M57 M58 M59 M60 M61 M62 M63 M64 M65 M66 M67 M68 M69 M7 M70 M71 M72 M73 M74 M75 M76 M77 M78 M79 M80 M81 M82 M83 M84 M85 M86 M87 M88 M89 M9 M90 M91 M92 M93 M94 M95 M96 M97 M98 M99 MAH MAL MAM MAR MAW MBE MBF MBR MC MCU MD MGM MHZ MIK MIL MIN MIO MIU MKD MKM MKW MLD MLT MMK MMQ MMT MND MNJ MON MPA MQD MQH MQM MQS MQW MRD MRM MRW MSK MTK MTQ MTR MTS MTZ MVA MWH N1 N10 N11 N12 N13 N14 N15 N16 N17 N18 N19 N20 N21 N22 N23 N24 N25 N26 N27 N28 N29 N3 N30 N31 N32 N33 N34 N35 N36 N37 N38 N39 N40 N41 N42 N43 N44 N45 N46 N47 N48 N49 N50 N51 N52 N53 N54 N55 N56 N57 N58 N59 N60 N61 N62 N63 N64 N65 N66 N67 N68 N69 N70 N71 N72 N73 N74 N75 N76 N77 N78 N79 N80 N81 N82 N83 N84 N85 N86 N87 N88 N89 N90 N91 N92 N93 N94 N95 N96 N97 N98 N99 NA NAR NCL NEW NF NIL NIU NL NM3 NMI NMP NPT NT NTU NU NX OA ODE ODG ODK ODM OHM ON ONZ OPM OT OZA OZI P1 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 P2 P20 P21 P22 P23 P24 P25 P26 P27 P28 P29 P30 P31 P32 P33 P34 P35 P36 P37 P38 P39 P40 P41 P42 P43 P44 P45 P46 P47 P48 P49 P5 P50 P51 P52 P53 P54 P55 P56 P57 P58 P59 P60 P61 P62 P63 P64 P65 P66 P67 P68 P69 P70 P71 P72 P73 P74 P75 P76 P77 P78 P79 P80 P81 P82 P83 P84 P85 P86 P87 P88 P89 P90 P91 P92 P93 P94 P95 P96 P97 P98 P99 PAL PD PFL PGL PI PLA PO PQ PR PS PTD PTI PTL PTN Q10 Q11 Q12 Q13 Q14 Q15 Q16 Q17 Q18 Q19 Q20 Q21 Q22 Q23 Q24 Q25 Q26 Q27 Q28 Q29 Q3 Q30 Q31 Q32 Q33 Q34 Q35 Q36 Q37 Q38 Q39 Q40 Q41 Q42 QA QAN QB QR QTD QTI QTL QTR R1 R9 RH RM ROM RP RPM RPS RT S3 S4 SAN SCO SCR SEC SET SG SIE SM3 SMI SQ SQR SR STC STI STK STL STN STW SW SX SYR T0 T3 TAH TAN TI TIC TIP TKM TMS TNE TP TPI TPR TQD TRL TST TTS U1 U2 UB UC VA VLT VP W2 WA WB WCD WE WEB WEE WG WHR WM WSD WTT X1 YDK YDQ YRD Z11 Z9 ZP ZZ X1A X1B X1D X1F X1G X1W X2C X3A X3H X43 X44 X4A X4B X4C X4D X4F X4G X4H X5H X5L X5M X6H X6P X7A X7B X8A X8B X8C XAA XAB XAC XAD XAE XAF XAG XAH XAI XAJ XAL XAM XAP XAT XAV XB4 XBA XBB XBC XBD XBE XBF XBG XBH XBI XBJ XBK XBL XBM XBN XBO XBP XBQ XBR XBS XBT XBU XBV XBW XBX XBY XBZ XCA XCB XCC XCD XCE XCF XCG XCH XCI XCJ XCK XCL XCM XCN XCO XCP XCQ XCR XCS XCT XCU XCV XCW XCX XCY XCZ XDA XDB XDC XDG XDH XDI XDJ XDK XDL XDM XDN XDP XDR XDS XDT XDU XDV XDW XDX XDY XEC XED XEE XEF XEG XEH XEI XEN XFB XFC XFD XFE XFI XFL XFO XFP XFR XFT XFW XFX XGB XGI XGL XGR XGU XGY XGZ XHA XHB XHC XHG XHN XHR XIA XIB XIC XID XIE XIF XIG XIH XIK XIL XIN XIZ XJB XJC XJG XJR XJT XJY XKG XKI XLE XLG XLT XLU XLV XLZ XMA XMB XMC XME XMR XMS XMT XMW XMX XNA XNE XNF XNG XNS XNT XNU XNV XO1 XO2 XO3 XO4 XO5 XO6 XO7 XO8 XO9 XOA XOB XOC XOD XOE XOF XOG XOH XOI XOJ XOK XOL XOM XON XOP XOQ XOR XOS XOT XOU XOV XOW XOX XOY XOZ XP1 XP2 XP3 XP4 XPA XPB XPC XPD XPE XPF XPG XPH XPI XPJ XPK XPL XPN XPO XPP XPR XPT XPU XPV XPX XPY XPZ XQA XQB XQC XQD XQF XQG XQH XQJ XQK XQL XQM XQN XQP XQQ XQR XQS XRD XRG XRJ XRK XRL XRO XRT XRZ XSA XSB XSC XSD XSE XSH XSI XSK XSL XSM XSO XSP XSS XST XSU XSV XSW XSX XSY XSZ XT1 XTB XTC XTD XTE XTG XTI XTK XTL XTN XTO XTR XTS XTT XTU XTV XTW XTY XTZ XUC XUN XVA XVG XVI XVK XVL XVN XVO XVP XVQ XVR XVS XVY XWA XWB XWC XWD XWF XWG XWH XWJ XWK XWL XWM XWN XWP XWQ XWR XWS XWT XWU XWV XWW XWX XWY XWZ XXA XXB XXC XXD XXF XXG XXH XXJ XXK XYA XYB XYC XYD XYF XYG XYH XYJ XYK XYL XYM XYN XYP XYQ XYR XYS XYT XYV XYW XYX XYY XYZ XZA XZB XZC XZD XZF XZG XZH XZJ XZK XZL XZM XZN XZP XZQ XZR XZS XZT XZU XZV XZW XZX XZY XZZ ', concat(' ', normalize-space(.), ' '))))" 
        id="BR-CL-003"
        flag="fatal"
        >[BR-CL-003]-Codul unității de masura(BT-13) TREBUIE să fie ales în conformitate cu Recomandarea UN/ECE nr. 20 şi Recomandarea UN/ECE nr 21.(<name/> = '<value-of select="."/>')</assert>
    </rule>
    <rule context="//@codTipOperatiune"> <!-- v2 -->
      <assert
        test="((not(contains(normalize-space(.), ' ')) and contains(' 10 12 14 20 22 24 30 40 50 60 70 ', concat(' ', normalize-space(.), ' '))))" 
        id="BR-CL-004"
        flag="fatal"
        >[BR-CL-004]-Codul operatiunii(BT-4) TREBUIE să fie ales din lista de coduri listTipOperatiune.(<name/> = '<value-of select="."/>')</assert>
    </rule>
    <rule context="//@codScopOperatiune"><!-- v2 -->
      <assert
        test="((not(contains(normalize-space(.), ' ')) and contains(' 101 201 301 401 501 601 703 704 705 801 802 901 1001 1101 9901 9999 ', concat(' ', normalize-space(.), ' '))))" 
        id="BR-CL-005"
        flag="fatal"
        >[BR-CL-005]-Codul scopului operatiunii(BT-8) TREBUIE să fie ales din lista de coduri listScopOperatiune.(<name/> = '<value-of select="."/>')</assert>
    </rule>
    <rule context="//@codPtf">
      <assert
        test="((not(contains(normalize-space(.), ' ')) and contains(' 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 ', concat(' ', normalize-space(.), ' '))))" 
        id="BR-CL-006"
        flag="fatal"
        >[BR-CL-006]-Codul Punctului de trecere a frontierei(BT-25) TREBUIE să fie ales din lista de coduri listPtf.(<name/> = '<value-of select="."/>')</assert>
    </rule>
    <rule context="//@codBirouVamal">
      <assert
        test="((not(contains(normalize-space(.), ' ')) and contains(' 12801 22801 22901 22902 32801 42801 42901 52801 52901 62801 72801 72901 72902 82801 92901 92902 102801 112801 112901 122801 122901 132901 132902 132903 132904 142801 152801 162801 162901 162902 162903 172901 172902 172903 172904 182801 192801 202801 212801 222901 222902 222903 232801 232901 242801 242901 242902 252901 252902 252903 252904 262801 262901 272801 282801 282802 292801 302801 302901 302902 312801 322801 322901 332801 332901 332902 332903 332904 342801 342901 342902 352802 352901 352902 352903 362901 362902 362903 362904 372801 372901 372902 382801 392801 402801 402802 402901 512801 522801 522901 ', concat(' ', normalize-space(.), ' '))))" 
        id="BR-CL-007"
        flag="fatal"
        >[BR-CL-007]-Codul Biroului vamal(BT-26) TREBUIE să fie ales din lista de coduri listBirouVamal.(<name/> = '<value-of select="."/>')</assert>
    </rule>
    <rule context="//@tipConfirmare">
      <assert
        test="((not(contains(normalize-space(.), ' ')) and contains(' 10 20 30 ', concat(' ', normalize-space(.), ' '))))" 
        id="BR-CL-008"
        flag="fatal"
        >[BR-CL-008]-Codul tipului de confirmare(BT-56) TREBUIE să fie ales din lista de coduri listTipConfirmare.(<name/> = '<value-of select="."/>')</assert>
    </rule>
    <rule context="//@tipDocument">
      <assert
        test="((not(contains(normalize-space(.), ' ')) and contains(' 10 20 30 9999 ', concat(' ', normalize-space(.), ' '))))" 
        id="BR-CL-009"
        flag="fatal"
        >[BR-CL-009]-Codul tipului de document(BT-47) TREBUIE să fie ales din lista de coduri listTipDocument.(<name/> = '<value-of select="."/>')</assert>
    </rule>
  </pattern> 
</schema>
