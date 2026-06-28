from pydantic import ConfigDict

from .ubl_unqualified_data_types_2_1 import (
    AmountType as UblUnqualifiedDataTypes21AmountType,
)
from .ubl_unqualified_data_types_2_1 import (
    BinaryObjectType,
    CodeType,
    IdentifierType,
    IndicatorType,
    NumericType,
    TimeType,
)
from .ubl_unqualified_data_types_2_1 import (
    DateType as UblUnqualifiedDataTypes21DateType,
)
from .ubl_unqualified_data_types_2_1 import (
    MeasureType as UblUnqualifiedDataTypes21MeasureType,
)
from .ubl_unqualified_data_types_2_1 import (
    NameType as UblUnqualifiedDataTypes21NameType,
)
from .ubl_unqualified_data_types_2_1 import (
    PercentType as UblUnqualifiedDataTypes21PercentType,
)
from .ubl_unqualified_data_types_2_1 import (
    QuantityType as UblUnqualifiedDataTypes21QuantityType,
)
from .ubl_unqualified_data_types_2_1 import (
    RateType as UblUnqualifiedDataTypes21RateType,
)
from .ubl_unqualified_data_types_2_1 import (
    TextType as UblUnqualifiedDataTypes21TextType,
)

__NAMESPACE__ = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"


class AcceptedIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class AcceptedVariantsDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class AccountFormatCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class AccountIdtype(IdentifierType):
    class Meta:
        name = "AccountIDType"

    model_config = ConfigDict(defer_build=True)


class AccountTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class AccountingCostCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class AccountingCostType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ActionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ActivityTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ActivityTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ActualDeliveryDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class ActualDeliveryTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ActualDespatchDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class ActualDespatchTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ActualPickupDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class ActualPickupTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ActualTemperatureReductionQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class AdValoremIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class AdditionalAccountIdtype(IdentifierType):
    class Meta:
        name = "AdditionalAccountIDType"

    model_config = ConfigDict(defer_build=True)


class AdditionalConditionsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class AdditionalInformationType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class AdditionalStreetNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class AddressFormatCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class AddressTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class AdjustmentReasonCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class AdmissionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class AdvertisementAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class AgencyIdtype(IdentifierType):
    class Meta:
        name = "AgencyIDType"

    model_config = ConfigDict(defer_build=True)


class AgencyNameType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class AirFlowPercentType(UblUnqualifiedDataTypes21PercentType):
    pass
    model_config = ConfigDict(defer_build=True)


class AircraftIdtype(IdentifierType):
    class Meta:
        name = "AircraftIDType"

    model_config = ConfigDict(defer_build=True)


class AliasNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class AllowanceChargeReasonCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class AllowanceChargeReasonType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class AllowanceTotalAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class AltitudeMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class AmountRateType(UblUnqualifiedDataTypes21RateType):
    pass
    model_config = ConfigDict(defer_build=True)


class AmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class AnimalFoodApprovedIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class AnimalFoodIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class AnnualAverageAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class ApplicationStatusCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ApprovalDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class ApprovalStatusType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class AttributeIdtype(IdentifierType):
    class Meta:
        name = "AttributeIDType"

    model_config = ConfigDict(defer_build=True)


class AuctionConstraintIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class AuctionUritype(IdentifierType):
    class Meta:
        name = "AuctionURIType"

    model_config = ConfigDict(defer_build=True)


class AvailabilityDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class AvailabilityStatusCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class AverageAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class AverageSubsequentContractAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class AwardDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class AwardTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class AwardingCriterionDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class AwardingCriterionIdtype(IdentifierType):
    class Meta:
        name = "AwardingCriterionIDType"

    model_config = ConfigDict(defer_build=True)


class AwardingCriterionTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class AwardingMethodTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class BackOrderAllowedIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class BackorderQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class BackorderReasonType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class BalanceAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class BalanceBroughtForwardIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class BarcodeSymbologyIdtype(IdentifierType):
    class Meta:
        name = "BarcodeSymbologyIDType"

    model_config = ConfigDict(defer_build=True)


class BaseAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class BaseQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class BaseUnitMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class BasedOnConsensusIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class BasicConsumedQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class BatchQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class BestBeforeDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class BindingOnBuyerIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class BirthDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class BirthplaceNameType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class BlockNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class BrandNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class BrokerAssignedIdtype(IdentifierType):
    class Meta:
        name = "BrokerAssignedIDType"

    model_config = ConfigDict(defer_build=True)


class BudgetYearNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class BuildingNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class BuildingNumberType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class BulkCargoIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class BusinessClassificationEvidenceIdtype(IdentifierType):
    class Meta:
        name = "BusinessClassificationEvidenceIDType"

    model_config = ConfigDict(defer_build=True)


class BusinessIdentityEvidenceIdtype(IdentifierType):
    class Meta:
        name = "BusinessIdentityEvidenceIDType"

    model_config = ConfigDict(defer_build=True)


class BuyerEventIdtype(IdentifierType):
    class Meta:
        name = "BuyerEventIDType"

    model_config = ConfigDict(defer_build=True)


class BuyerProfileUritype(IdentifierType):
    class Meta:
        name = "BuyerProfileURIType"

    model_config = ConfigDict(defer_build=True)


class BuyerReferenceType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class Cv2Idtype(IdentifierType):
    class Meta:
        name = "CV2IDType"

    model_config = ConfigDict(defer_build=True)


class CalculationExpressionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CalculationExpressionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class CalculationMethodCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CalculationRateType(UblUnqualifiedDataTypes21RateType):
    pass
    model_config = ConfigDict(defer_build=True)


class CalculationSequenceNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class CallBaseAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class CallDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class CallExtensionAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class CallTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CancellationNoteType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class CandidateReductionConstraintIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class CandidateStatementType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class CanonicalizationMethodType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class CapabilityTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CardChipCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CardTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CargoTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CarrierAssignedIdtype(IdentifierType):
    class Meta:
        name = "CarrierAssignedIDType"

    model_config = ConfigDict(defer_build=True)


class CarrierServiceInstructionsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class CatalogueIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class CategoryNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class CertificateTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CertificateTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ChangeConditionsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ChannelCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ChannelType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class CharacterSetCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CharacteristicsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ChargeIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class ChargeTotalAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class ChargeableQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ChargeableWeightMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class ChildConsignmentQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ChipApplicationIdtype(IdentifierType):
    class Meta:
        name = "ChipApplicationIDType"

    model_config = ConfigDict(defer_build=True)


class CityNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class CitySubdivisionNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class CodeValueType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class CollaborationPriorityCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CommentType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class CommodityCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CompanyIdtype(IdentifierType):
    class Meta:
        name = "CompanyIDType"

    model_config = ConfigDict(defer_build=True)


class CompanyLegalFormCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CompanyLegalFormType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class CompanyLiquidationStatusCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ComparedValueMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class ComparisonDataCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ComparisonDataSourceCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ComparisonForecastIssueDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class ComparisonForecastIssueTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CompletionIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConditionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConditionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConditionsDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConditionsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConsigneeAssignedIdtype(IdentifierType):
    class Meta:
        name = "ConsigneeAssignedIDType"

    model_config = ConfigDict(defer_build=True)


class ConsignmentQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConsignorAssignedIdtype(IdentifierType):
    class Meta:
        name = "ConsignorAssignedIDType"

    model_config = ConfigDict(defer_build=True)


class ConsolidatableIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConstitutionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConsumerIncentiveTacticTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConsumerUnitQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConsumersEnergyLevelCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConsumersEnergyLevelType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConsumptionEnergyQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConsumptionIdtype(IdentifierType):
    class Meta:
        name = "ConsumptionIDType"

    model_config = ConfigDict(defer_build=True)


class ConsumptionLevelCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConsumptionLevelType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConsumptionReportIdtype(IdentifierType):
    class Meta:
        name = "ConsumptionReportIDType"

    model_config = ConfigDict(defer_build=True)


class ConsumptionTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConsumptionTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ConsumptionWaterQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ContainerizedIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class ContentType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ContentUnitQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ContractFolderIdtype(IdentifierType):
    class Meta:
        name = "ContractFolderIDType"

    model_config = ConfigDict(defer_build=True)


class ContractNameType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ContractSubdivisionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ContractTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ContractTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ContractedCarrierAssignedIdtype(IdentifierType):
    class Meta:
        name = "ContractedCarrierAssignedIDType"

    model_config = ConfigDict(defer_build=True)


class ContractingSystemCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CoordinateSystemCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CopyIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class CorporateRegistrationTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CorporateStockAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class CorrectionAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class CorrectionTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CorrectionTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class CorrectionUnitAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class CountrySubentityCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CountrySubentityType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class CreditLineAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class CreditNoteTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CreditedQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class CrewQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class CurrencyCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CurrentChargeTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CurrentChargeTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class CustomerAssignedAccountIdtype(IdentifierType):
    class Meta:
        name = "CustomerAssignedAccountIDType"

    model_config = ConfigDict(defer_build=True)


class CustomerReferenceType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class CustomizationIdtype(IdentifierType):
    class Meta:
        name = "CustomizationIDType"

    model_config = ConfigDict(defer_build=True)


class CustomsClearanceServiceInstructionsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class CustomsImportClassifiedIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class CustomsStatusCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class CustomsTariffQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class DamageRemarksType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class DangerousGoodsApprovedIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class DataSendingCapabilityType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class DataSourceCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class DateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class DebitLineAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class DebitedQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class DeclarationTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class DeclaredCarriageValueAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class DeclaredCustomsValueAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class DeclaredForCarriageValueAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class DeclaredStatisticsValueAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class DeliveredQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class DeliveryInstructionsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class DemurrageInstructionsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class DepartmentType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class DescriptionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class DescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class DespatchAdviceTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class DifferenceTemperatureReductionQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class DirectionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class DisplayTacticTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class DispositionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class DistrictType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class DocumentCurrencyCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class DocumentDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class DocumentHashType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class DocumentIdtype(IdentifierType):
    class Meta:
        name = "DocumentIDType"

    model_config = ConfigDict(defer_build=True)


class DocumentStatusCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class DocumentStatusReasonCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class DocumentStatusReasonDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class DocumentTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class DocumentTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class DocumentationFeeAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class DueDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class DurationMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class DutyCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class DutyType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class EarliestPickupDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class EarliestPickupTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class EconomicOperatorRegistryUritype(IdentifierType):
    class Meta:
        name = "EconomicOperatorRegistryURIType"

    model_config = ConfigDict(defer_build=True)


class EffectiveDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class EffectiveTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ElectronicDeviceDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ElectronicMailType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class EmbeddedDocumentBinaryObjectType(BinaryObjectType):
    pass
    model_config = ConfigDict(defer_build=True)


class EmergencyProceduresCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class EmployeeQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class EncodingCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class EndDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class EndTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class EndpointIdtype(IdentifierType):
    class Meta:
        name = "EndpointIDType"

    model_config = ConfigDict(defer_build=True)


class EnvironmentalEmissionTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class EstimatedAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class EstimatedConsumedQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class EstimatedDeliveryDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class EstimatedDeliveryTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class EstimatedDespatchDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class EstimatedDespatchTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class EstimatedOverallContractAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class EstimatedOverallContractQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class EvaluationCriterionTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class EvidenceTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExceptionResolutionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExceptionStatusCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExchangeMarketIdtype(IdentifierType):
    class Meta:
        name = "ExchangeMarketIDType"

    model_config = ConfigDict(defer_build=True)


class ExclusionReasonType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExecutionRequirementCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExemptionReasonCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExemptionReasonType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExpectedOperatorQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExpectedQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExpenseCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExpiryDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExpiryTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExpressionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExpressionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ExtendedIdtype(IdentifierType):
    class Meta:
        name = "ExtendedIDType"

    model_config = ConfigDict(defer_build=True)


class ExtensionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class FaceValueAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class FamilyNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class FeatureTacticTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class FeeAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class FeeDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class FileNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class FinancingInstrumentCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class FirstNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class FirstShipmentAvailibilityDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class FloorType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class FollowupContractIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class ForecastPurposeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ForecastTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class FormatCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ForwarderServiceInstructionsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class FreeOfChargeIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class FreeOnBoardValueAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class FreightForwarderAssignedIdtype(IdentifierType):
    class Meta:
        name = "FreightForwarderAssignedIDType"

    model_config = ConfigDict(defer_build=True)


class FreightRateClassCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class FrequencyType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class FrozenDocumentIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class FrozenPeriodDaysNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class FullnessIndicationCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class FullyPaidSharesIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class FundingProgramCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class FundingProgramType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class GasPressureQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class GenderCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class GeneralCargoIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class GovernmentAgreementConstraintIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class GrossTonnageMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class GrossVolumeMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class GrossWeightMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class GuaranteeTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class GuaranteedDespatchDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class GuaranteedDespatchTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class HandlingCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class HandlingInstructionsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class HashAlgorithmMethodType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class HaulageInstructionsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class HazardClassIdtype(IdentifierType):
    class Meta:
        name = "HazardClassIDType"

    model_config = ConfigDict(defer_build=True)


class HazardousCategoryCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class HazardousRegulationCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class HazardousRiskIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class HeatingTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class HeatingTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class HigherTenderAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class HolderNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class HumanFoodApprovedIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class HumanFoodIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class HumidityPercentType(UblUnqualifiedDataTypes21PercentType):
    pass
    model_config = ConfigDict(defer_build=True)


class Idtype(IdentifierType):
    class Meta:
        name = "IDType"

    model_config = ConfigDict(defer_build=True)


class IdentificationCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class IdentificationIdtype(IdentifierType):
    class Meta:
        name = "IdentificationIDType"

    model_config = ConfigDict(defer_build=True)


class ImmobilizationCertificateIdtype(IdentifierType):
    class Meta:
        name = "ImmobilizationCertificateIDType"

    model_config = ConfigDict(defer_build=True)


class ImportanceCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class IndicationIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class IndustryClassificationCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class InformationType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class InformationUritype(IdentifierType):
    class Meta:
        name = "InformationURIType"

    model_config = ConfigDict(defer_build=True)


class InhalationToxicityZoneCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class InhouseMailType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class InspectionMethodCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class InstallmentDueDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class InstructionIdtype(IdentifierType):
    class Meta:
        name = "InstructionIDType"

    model_config = ConfigDict(defer_build=True)


class InstructionNoteType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class InstructionsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class InsurancePremiumAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class InsuranceValueAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class InventoryValueAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class InvoiceTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class InvoicedQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class InvoicingPartyReferenceType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class IssueDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class IssueNumberIdtype(IdentifierType):
    class Meta:
        name = "IssueNumberIDType"

    model_config = ConfigDict(defer_build=True)


class IssueTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class IssuerIdtype(IdentifierType):
    class Meta:
        name = "IssuerIDType"

    model_config = ConfigDict(defer_build=True)


class ItemClassificationCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ItemUpdateRequestIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class JobTitleType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class JourneyIdtype(IdentifierType):
    class Meta:
        name = "JourneyIDType"

    model_config = ConfigDict(defer_build=True)


class JustificationDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class JustificationType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class KeywordType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class LanguageIdtype(IdentifierType):
    class Meta:
        name = "LanguageIDType"

    model_config = ConfigDict(defer_build=True)


class LastRevisionDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class LastRevisionTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class LatestDeliveryDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class LatestDeliveryTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class LatestMeterQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class LatestMeterReadingDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class LatestMeterReadingMethodCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class LatestMeterReadingMethodType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class LatestPickupDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class LatestPickupTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class LatestProposalAcceptanceDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class LatestSecurityClearanceDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class LatitudeDegreesMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class LatitudeDirectionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class LatitudeMinutesMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class LeadTimeMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class LegalReferenceType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class LegalStatusIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class LiabilityAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class LicensePlateIdtype(IdentifierType):
    class Meta:
        name = "LicensePlateIDType"

    model_config = ConfigDict(defer_build=True)


class LifeCycleStatusCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class LimitationDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class LineCountNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class LineExtensionAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class LineIdtype(IdentifierType):
    class Meta:
        name = "LineIDType"

    model_config = ConfigDict(defer_build=True)


class LineNumberNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class LineStatusCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class LineType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ListValueType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class LivestockIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class LoadingLengthMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class LoadingSequenceIdtype(IdentifierType):
    class Meta:
        name = "LoadingSequenceIDType"

    model_config = ConfigDict(defer_build=True)


class LocaleCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class LocationIdtype(IdentifierType):
    class Meta:
        name = "LocationIDType"

    model_config = ConfigDict(defer_build=True)


class LocationType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class LocationTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class LoginType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class LogoReferenceIdtype(IdentifierType):
    class Meta:
        name = "LogoReferenceIDType"

    model_config = ConfigDict(defer_build=True)


class LongitudeDegreesMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class LongitudeDirectionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class LongitudeMinutesMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class LossRiskResponsibilityCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class LossRiskType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class LotNumberIdtype(IdentifierType):
    class Meta:
        name = "LotNumberIDType"

    model_config = ConfigDict(defer_build=True)


class LowTendersDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class LowerOrangeHazardPlacardIdtype(IdentifierType):
    class Meta:
        name = "LowerOrangeHazardPlacardIDType"

    model_config = ConfigDict(defer_build=True)


class LowerTenderAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class MandateTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ManufactureDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class ManufactureTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class MarkAttentionIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class MarkAttentionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class MarkCareIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class MarkCareType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class MarketValueAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class MarkingIdtype(IdentifierType):
    class Meta:
        name = "MarkingIDType"

    model_config = ConfigDict(defer_build=True)


class MathematicOperatorCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class MaximumAdvertisementAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class MaximumAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class MaximumBackorderQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class MaximumCopiesNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class MaximumMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class MaximumNumberNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class MaximumOperatorQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class MaximumOrderQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class MaximumPaidAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class MaximumPaymentInstructionsNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class MaximumPercentType(UblUnqualifiedDataTypes21PercentType):
    pass
    model_config = ConfigDict(defer_build=True)


class MaximumQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class MaximumValueType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class MaximumVariantQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class MeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class MedicalFirstAidGuideCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class MeterConstantCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class MeterConstantType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class MeterNameType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class MeterNumberType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class MeterReadingCommentsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class MeterReadingTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class MeterReadingTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class MiddleNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class MimeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class MinimumAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class MinimumBackorderQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class MinimumImprovementBidType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class MinimumInventoryQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class MinimumMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class MinimumNumberNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class MinimumOrderQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class MinimumPercentType(UblUnqualifiedDataTypes21PercentType):
    pass
    model_config = ConfigDict(defer_build=True)


class MinimumQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class MinimumValueType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class MiscellaneousEventTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ModelNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class MonetaryScopeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class MovieTitleType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class MultipleOrderQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class MultiplierFactorNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class NameCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class NameSuffixType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class NameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class NationalityIdtype(IdentifierType):
    class Meta:
        name = "NationalityIDType"

    model_config = ConfigDict(defer_build=True)


class NatureCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class NegotiationDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class NetNetWeightMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class NetTonnageMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class NetVolumeMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class NetWeightMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class NetworkIdtype(IdentifierType):
    class Meta:
        name = "NetworkIDType"

    model_config = ConfigDict(defer_build=True)


class NominationDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class NominationTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class NormalTemperatureReductionQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class NoteType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class NotificationTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class OccurrenceDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class OccurrenceTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class OnCarriageIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class OneTimeChargeTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class OneTimeChargeTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class OntologyUritype(IdentifierType):
    class Meta:
        name = "OntologyURIType"

    model_config = ConfigDict(defer_build=True)


class OpenTenderIdtype(IdentifierType):
    class Meta:
        name = "OpenTenderIDType"

    model_config = ConfigDict(defer_build=True)


class OperatingYearsQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class OptionalLineItemIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class OptionsDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class OrderIntervalDaysNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class OrderQuantityIncrementNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class OrderResponseCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class OrderTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class OrderableIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class OrderableUnitFactorRateType(UblUnqualifiedDataTypes21RateType):
    pass
    model_config = ConfigDict(defer_build=True)


class OrderableUnitType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class OrganizationDepartmentType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class OriginalContractingSystemIdtype(IdentifierType):
    class Meta:
        name = "OriginalContractingSystemIDType"

    model_config = ConfigDict(defer_build=True)


class OriginalJobIdtype(IdentifierType):
    class Meta:
        name = "OriginalJobIDType"

    model_config = ConfigDict(defer_build=True)


class OtherConditionsIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class OtherInstructionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class OtherNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class OutstandingQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class OutstandingReasonType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class OversupplyQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class OwnerTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PackLevelCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PackQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class PackSizeNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class PackageLevelCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PackagingTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PackingCriteriaCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PackingMaterialType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PaidAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class PaidDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class PaidTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ParentDocumentIdtype(IdentifierType):
    class Meta:
        name = "ParentDocumentIDType"

    model_config = ConfigDict(defer_build=True)


class ParentDocumentLineReferenceIdtype(IdentifierType):
    class Meta:
        name = "ParentDocumentLineReferenceIDType"

    model_config = ConfigDict(defer_build=True)


class ParentDocumentTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ParentDocumentVersionIdtype(IdentifierType):
    class Meta:
        name = "ParentDocumentVersionIDType"

    model_config = ConfigDict(defer_build=True)


class PartPresentationCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PartecipationPercentType(UblUnqualifiedDataTypes21PercentType):
    pass
    model_config = ConfigDict(defer_build=True)


class PartialDeliveryIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class ParticipationPercentType(UblUnqualifiedDataTypes21PercentType):
    pass
    model_config = ConfigDict(defer_build=True)


class PartyCapacityAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class PartyTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PartyTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PassengerQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class PasswordType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PayPerViewType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PayableAlternativeAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class PayableAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class PayableRoundingAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class PayerReferenceType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PaymentAlternativeCurrencyCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PaymentChannelCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PaymentCurrencyCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PaymentDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PaymentDueDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class PaymentFrequencyCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PaymentIdtype(IdentifierType):
    class Meta:
        name = "PaymentIDType"

    model_config = ConfigDict(defer_build=True)


class PaymentMeansCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PaymentMeansIdtype(IdentifierType):
    class Meta:
        name = "PaymentMeansIDType"

    model_config = ConfigDict(defer_build=True)


class PaymentNoteType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PaymentOrderReferenceType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PaymentPercentType(UblUnqualifiedDataTypes21PercentType):
    pass
    model_config = ConfigDict(defer_build=True)


class PaymentPurposeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PaymentTermsDetailsUritype(IdentifierType):
    class Meta:
        name = "PaymentTermsDetailsURIType"

    model_config = ConfigDict(defer_build=True)


class PenaltyAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class PenaltySurchargePercentType(UblUnqualifiedDataTypes21PercentType):
    pass
    model_config = ConfigDict(defer_build=True)


class PerUnitAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class PercentType(UblUnqualifiedDataTypes21PercentType):
    pass
    model_config = ConfigDict(defer_build=True)


class PerformanceMetricTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PerformanceValueQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class PerformingCarrierAssignedIdtype(IdentifierType):
    class Meta:
        name = "PerformingCarrierAssignedIDType"

    model_config = ConfigDict(defer_build=True)


class PersonalSituationType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PhoneNumberType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PlacardEndorsementType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PlacardNotationType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PlannedDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class PlotIdentificationType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PositionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PostEventNotificationDurationMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class PostalZoneType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PostboxType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PowerIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class PreCarriageIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class PreEventNotificationDurationMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class PreferenceCriterionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PrepaidAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class PrepaidIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class PrepaidPaymentReferenceIdtype(IdentifierType):
    class Meta:
        name = "PrepaidPaymentReferenceIDType"

    model_config = ConfigDict(defer_build=True)


class PreviousCancellationReasonCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PreviousJobIdtype(IdentifierType):
    class Meta:
        name = "PreviousJobIDType"

    model_config = ConfigDict(defer_build=True)


class PreviousMeterQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class PreviousMeterReadingDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class PreviousMeterReadingMethodCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PreviousMeterReadingMethodType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PreviousVersionIdtype(IdentifierType):
    class Meta:
        name = "PreviousVersionIDType"

    model_config = ConfigDict(defer_build=True)


class PriceAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class PriceChangeReasonType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PriceEvaluationCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PriceRevisionFormulaDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PriceTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PriceTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PricingCurrencyCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PricingUpdateRequestIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class PrimaryAccountNumberIdtype(IdentifierType):
    class Meta:
        name = "PrimaryAccountNumberIDType"

    model_config = ConfigDict(defer_build=True)


class PrintQualifierType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PriorityType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PrivacyCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PrizeDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class PrizeIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class ProcedureCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ProcessDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ProcessReasonCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ProcessReasonType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ProcurementSubTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ProcurementTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ProductTraceIdtype(IdentifierType):
    class Meta:
        name = "ProductTraceIDType"

    model_config = ConfigDict(defer_build=True)


class ProfileExecutionIdtype(IdentifierType):
    class Meta:
        name = "ProfileExecutionIDType"

    model_config = ConfigDict(defer_build=True)


class ProfileIdtype(IdentifierType):
    class Meta:
        name = "ProfileIDType"

    model_config = ConfigDict(defer_build=True)


class ProfileStatusCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ProgressPercentType(UblUnqualifiedDataTypes21PercentType):
    pass
    model_config = ConfigDict(defer_build=True)


class PromotionalEventTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ProviderTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PublishAwardIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class PurposeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class PurposeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class QualityControlCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class QuantityDiscrepancyCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class QuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class RadioCallSignIdtype(IdentifierType):
    class Meta:
        name = "RadioCallSignIDType"

    model_config = ConfigDict(defer_build=True)


class RailCarIdtype(IdentifierType):
    class Meta:
        name = "RailCarIDType"

    model_config = ConfigDict(defer_build=True)


class RankType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class RateType(UblUnqualifiedDataTypes21RateType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReceiptAdviceTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReceivedDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReceivedElectronicTenderQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReceivedForeignTenderQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReceivedQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReceivedTenderQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReferenceDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReferenceEventCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReferenceIdtype(IdentifierType):
    class Meta:
        name = "ReferenceIDType"

    model_config = ConfigDict(defer_build=True)


class ReferenceTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReferenceType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReferencedConsignmentIdtype(IdentifierType):
    class Meta:
        name = "ReferencedConsignmentIDType"

    model_config = ConfigDict(defer_build=True)


class RefrigeratedIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class RefrigerationOnIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class RegionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class RegisteredDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class RegisteredTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class RegistrationDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class RegistrationExpirationDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class RegistrationIdtype(IdentifierType):
    class Meta:
        name = "RegistrationIDType"

    model_config = ConfigDict(defer_build=True)


class RegistrationNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class RegistrationNationalityIdtype(IdentifierType):
    class Meta:
        name = "RegistrationNationalityIDType"

    model_config = ConfigDict(defer_build=True)


class RegistrationNationalityType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class RegulatoryDomainType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class RejectActionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class RejectReasonCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class RejectReasonType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class RejectedQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class RejectionNoteType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReleaseIdtype(IdentifierType):
    class Meta:
        name = "ReleaseIDType"

    model_config = ConfigDict(defer_build=True)


class ReliabilityPercentType(UblUnqualifiedDataTypes21PercentType):
    pass
    model_config = ConfigDict(defer_build=True)


class RemarksType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReminderSequenceNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReminderTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReplenishmentOwnerDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class RequestForQuotationLineIdtype(IdentifierType):
    class Meta:
        name = "RequestForQuotationLineIDType"

    model_config = ConfigDict(defer_build=True)


class RequestedDeliveryDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class RequestedDespatchDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class RequestedDespatchTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class RequestedInvoiceCurrencyCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class RequestedPublicationDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class RequiredCurriculaIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class RequiredCustomsIdtype(IdentifierType):
    class Meta:
        name = "RequiredCustomsIDType"

    model_config = ConfigDict(defer_build=True)


class RequiredDeliveryDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class RequiredDeliveryTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class RequiredFeeAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class ResidenceTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ResidenceTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ResidentOccupantsNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class ResolutionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ResolutionDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class ResolutionTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ResolutionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ResponseCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ResponseDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class ResponseTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class RetailEventNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class RetailEventStatusCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReturnabilityIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReturnableMaterialIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class ReturnableQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class RevisedForecastLineIdtype(IdentifierType):
    class Meta:
        name = "RevisedForecastLineIDType"

    model_config = ConfigDict(defer_build=True)


class RevisionDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class RevisionStatusCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class RevisionTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class RoamingPartnerNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class RoleCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class RoleDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class RoomType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class RoundingAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class SalesOrderIdtype(IdentifierType):
    class Meta:
        name = "SalesOrderIDType"

    model_config = ConfigDict(defer_build=True)


class SalesOrderLineIdtype(IdentifierType):
    class Meta:
        name = "SalesOrderLineIDType"

    model_config = ConfigDict(defer_build=True)


class SchemeUritype(IdentifierType):
    class Meta:
        name = "SchemeURIType"

    model_config = ConfigDict(defer_build=True)


class SealIssuerTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class SealStatusCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class SealingPartyTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class SecurityClassificationCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class SecurityIdtype(IdentifierType):
    class Meta:
        name = "SecurityIDType"

    model_config = ConfigDict(defer_build=True)


class SellerEventIdtype(IdentifierType):
    class Meta:
        name = "SellerEventIDType"

    model_config = ConfigDict(defer_build=True)


class SequenceIdtype(IdentifierType):
    class Meta:
        name = "SequenceIDType"

    model_config = ConfigDict(defer_build=True)


class SequenceNumberIdtype(IdentifierType):
    class Meta:
        name = "SequenceNumberIDType"

    model_config = ConfigDict(defer_build=True)


class SequenceNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class SerialIdtype(IdentifierType):
    class Meta:
        name = "SerialIDType"

    model_config = ConfigDict(defer_build=True)


class ServiceInformationPreferenceCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ServiceNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class ServiceNumberCalledType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ServiceTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ServiceTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class SettlementDiscountAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class SettlementDiscountPercentType(UblUnqualifiedDataTypes21PercentType):
    pass
    model_config = ConfigDict(defer_build=True)


class SharesNumberQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ShippingMarksType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ShippingOrderIdtype(IdentifierType):
    class Meta:
        name = "ShippingOrderIDType"

    model_config = ConfigDict(defer_build=True)


class ShippingPriorityLevelCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ShipsRequirementsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ShortQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ShortageActionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class SignatureIdtype(IdentifierType):
    class Meta:
        name = "SignatureIDType"

    model_config = ConfigDict(defer_build=True)


class SignatureMethodType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class SizeTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class SoleProprietorshipIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class SourceCurrencyBaseRateType(UblUnqualifiedDataTypes21RateType):
    pass
    model_config = ConfigDict(defer_build=True)


class SourceCurrencyCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class SourceForecastIssueDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class SourceForecastIssueTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class SourceValueMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class SpecialInstructionsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class SpecialSecurityIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class SpecialServiceInstructionsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class SpecialTermsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class SpecialTransportRequirementsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class SpecificationIdtype(IdentifierType):
    class Meta:
        name = "SpecificationIDType"

    model_config = ConfigDict(defer_build=True)


class SpecificationTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class SplitConsignmentIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class StartDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class StartTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class StatementTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class StatusAvailableIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class StatusCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class StatusReasonCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class StatusReasonType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class StreetNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class SubcontractingConditionsCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class SubmissionDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class SubmissionDueDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class SubmissionMethodCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class SubscriberIdtype(IdentifierType):
    class Meta:
        name = "SubscriberIDType"

    model_config = ConfigDict(defer_build=True)


class SubscriberTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class SubscriberTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class SubstitutionStatusCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class SuccessiveSequenceIdtype(IdentifierType):
    class Meta:
        name = "SuccessiveSequenceIDType"

    model_config = ConfigDict(defer_build=True)


class SummaryDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class SupplierAssignedAccountIdtype(IdentifierType):
    class Meta:
        name = "SupplierAssignedAccountIDType"

    model_config = ConfigDict(defer_build=True)


class SupplyChainActivityTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TareWeightMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class TargetCurrencyBaseRateType(UblUnqualifiedDataTypes21RateType):
    pass
    model_config = ConfigDict(defer_build=True)


class TargetCurrencyCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TargetInventoryQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class TargetServicePercentType(UblUnqualifiedDataTypes21PercentType):
    pass
    model_config = ConfigDict(defer_build=True)


class TariffClassCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TariffCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TariffDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TaxAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TaxCurrencyCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TaxEnergyAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TaxEnergyBalanceAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TaxEnergyOnAccountAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TaxEvidenceIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class TaxExclusiveAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TaxExemptionReasonCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TaxExemptionReasonType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TaxIncludedIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class TaxInclusiveAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TaxLevelCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TaxPointDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class TaxTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TaxableAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TechnicalCommitteeDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TechnicalNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class TelecommunicationsServiceCallCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TelecommunicationsServiceCallType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TelecommunicationsServiceCategoryCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TelecommunicationsServiceCategoryType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TelecommunicationsSupplyTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TelecommunicationsSupplyTypeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TelefaxType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TelephoneType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TenderEnvelopeIdtype(IdentifierType):
    class Meta:
        name = "TenderEnvelopeIDType"

    model_config = ConfigDict(defer_build=True)


class TenderEnvelopeTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TenderResultCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TenderTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TendererRequirementTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TendererRoleCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TestMethodType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TextType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ThirdPartyPayerIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class ThresholdAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class ThresholdQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ThresholdValueComparisonCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TierRangeType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TierRatePercentType(UblUnqualifiedDataTypes21PercentType):
    pass
    model_config = ConfigDict(defer_build=True)


class TimeAmountType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TimeDeltaDaysQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class TimeFrequencyCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TimezoneOffsetType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TimingComplaintCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TimingComplaintType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TitleType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ToOrderIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class TotalAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TotalBalanceAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TotalConsumedQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class TotalCreditAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TotalDebitAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TotalDeliveredQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class TotalGoodsItemQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class TotalInvoiceAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TotalMeteredQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class TotalPackageQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class TotalPackagesQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class TotalPaymentAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TotalTaskAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TotalTaxAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TotalTransportHandlingUnitQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class TraceIdtype(IdentifierType):
    class Meta:
        name = "TraceIDType"

    model_config = ConfigDict(defer_build=True)


class TrackingDeviceCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TrackingIdtype(IdentifierType):
    class Meta:
        name = "TrackingIDType"

    model_config = ConfigDict(defer_build=True)


class TradeItemPackingLabelingTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TradeServiceCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TradingRestrictionsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TrainIdtype(IdentifierType):
    class Meta:
        name = "TrainIDType"

    model_config = ConfigDict(defer_build=True)


class TransactionCurrencyTaxAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransitDirectionCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransportAuthorizationCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransportEmergencyCardCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransportEquipmentTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransportEventTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransportExecutionPlanReferenceIdtype(IdentifierType):
    class Meta:
        name = "TransportExecutionPlanReferenceIDType"

    model_config = ConfigDict(defer_build=True)


class TransportExecutionStatusCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransportHandlingUnitTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransportMeansTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransportModeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransportServiceCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransportServiceProviderRemarksType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransportServiceProviderSpecialTermsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransportUserRemarksType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransportUserSpecialTermsType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransportationServiceDescriptionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class TransportationServiceDetailsUritype(IdentifierType):
    class Meta:
        name = "TransportationServiceDetailsURIType"

    model_config = ConfigDict(defer_build=True)


class TransportationStatusTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class TypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class UblversionIdtype(IdentifierType):
    class Meta:
        name = "UBLVersionIDType"

    model_config = ConfigDict(defer_build=True)


class UndgcodeType(CodeType):
    class Meta:
        name = "UNDGCodeType"

    model_config = ConfigDict(defer_build=True)


class Uritype(IdentifierType):
    class Meta:
        name = "URIType"

    model_config = ConfigDict(defer_build=True)


class Uuidtype(IdentifierType):
    class Meta:
        name = "UUIDType"

    model_config = ConfigDict(defer_build=True)


class UnknownPriceIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class UpperOrangeHazardPlacardIdtype(IdentifierType):
    class Meta:
        name = "UpperOrangeHazardPlacardIDType"

    model_config = ConfigDict(defer_build=True)


class UrgencyCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class UtilityStatementTypeCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ValidateProcessType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ValidateToolType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ValidateToolVersionType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ValidationDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class ValidationResultCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ValidationTimeType(TimeType):
    pass
    model_config = ConfigDict(defer_build=True)


class ValidatorIdtype(IdentifierType):
    class Meta:
        name = "ValidatorIDType"

    model_config = ConfigDict(defer_build=True)


class ValidityStartDateType(UblUnqualifiedDataTypes21DateType):
    pass
    model_config = ConfigDict(defer_build=True)


class ValueAmountType(UblUnqualifiedDataTypes21AmountType):
    pass
    model_config = ConfigDict(defer_build=True)


class ValueMeasureType(UblUnqualifiedDataTypes21MeasureType):
    pass
    model_config = ConfigDict(defer_build=True)


class ValueQualifierType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class ValueQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class ValueType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class VarianceQuantityType(UblUnqualifiedDataTypes21QuantityType):
    pass
    model_config = ConfigDict(defer_build=True)


class VariantConstraintIndicatorType(IndicatorType):
    pass
    model_config = ConfigDict(defer_build=True)


class VariantIdtype(IdentifierType):
    class Meta:
        name = "VariantIDType"

    model_config = ConfigDict(defer_build=True)


class VersionIdtype(IdentifierType):
    class Meta:
        name = "VersionIDType"

    model_config = ConfigDict(defer_build=True)


class VesselIdtype(IdentifierType):
    class Meta:
        name = "VesselIDType"

    model_config = ConfigDict(defer_build=True)


class VesselNameType(UblUnqualifiedDataTypes21NameType):
    pass
    model_config = ConfigDict(defer_build=True)


class WarrantyInformationType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class WebsiteUritype(IdentifierType):
    class Meta:
        name = "WebsiteURIType"

    model_config = ConfigDict(defer_build=True)


class WeekDayCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class WeightNumericType(NumericType):
    pass
    model_config = ConfigDict(defer_build=True)


class WeightType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class WeightingAlgorithmCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class WorkPhaseCodeType(CodeType):
    pass
    model_config = ConfigDict(defer_build=True)


class WorkPhaseType(UblUnqualifiedDataTypes21TextType):
    pass
    model_config = ConfigDict(defer_build=True)


class XpathType(UblUnqualifiedDataTypes21TextType):
    class Meta:
        name = "XPathType"

    model_config = ConfigDict(defer_build=True)


class AcceptedIndicator(AcceptedIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AcceptedVariantsDescription(AcceptedVariantsDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AccountFormatCode(AccountFormatCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AccountId(AccountIdtype):
    class Meta:
        name = "AccountID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AccountTypeCode(AccountTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AccountingCost(AccountingCostType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AccountingCostCode(AccountingCostCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ActionCode(ActionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ActivityType(ActivityTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ActivityTypeCode(ActivityTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ActualDeliveryDate(ActualDeliveryDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ActualDeliveryTime(ActualDeliveryTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ActualDespatchDate(ActualDespatchDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ActualDespatchTime(ActualDespatchTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ActualPickupDate(ActualPickupDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ActualPickupTime(ActualPickupTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ActualTemperatureReductionQuantity(ActualTemperatureReductionQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AdValoremIndicator(AdValoremIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AdditionalAccountId(AdditionalAccountIdtype):
    class Meta:
        name = "AdditionalAccountID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AdditionalConditions(AdditionalConditionsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AdditionalInformation(AdditionalInformationType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AdditionalStreetName(AdditionalStreetNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AddressFormatCode(AddressFormatCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AddressTypeCode(AddressTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AdjustmentReasonCode(AdjustmentReasonCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AdmissionCode(AdmissionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AdvertisementAmount(AdvertisementAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AgencyId(AgencyIdtype):
    class Meta:
        name = "AgencyID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AgencyName(AgencyNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AirFlowPercent(AirFlowPercentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AircraftId(AircraftIdtype):
    class Meta:
        name = "AircraftID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AliasName(AliasNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AllowanceChargeReason(AllowanceChargeReasonType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AllowanceChargeReasonCode(AllowanceChargeReasonCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AllowanceTotalAmount(AllowanceTotalAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AltitudeMeasure(AltitudeMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Amount(AmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AmountRate(AmountRateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AnimalFoodApprovedIndicator(AnimalFoodApprovedIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AnimalFoodIndicator(AnimalFoodIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AnnualAverageAmount(AnnualAverageAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ApplicationStatusCode(ApplicationStatusCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ApprovalDate(ApprovalDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ApprovalStatus(ApprovalStatusType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AttributeId(AttributeIdtype):
    class Meta:
        name = "AttributeID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AuctionConstraintIndicator(AuctionConstraintIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AuctionUri(AuctionUritype):
    class Meta:
        name = "AuctionURI"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AvailabilityDate(AvailabilityDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AvailabilityStatusCode(AvailabilityStatusCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AverageAmount(AverageAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AverageSubsequentContractAmount(AverageSubsequentContractAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AwardDate(AwardDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AwardTime(AwardTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AwardingCriterionDescription(AwardingCriterionDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AwardingCriterionId(AwardingCriterionIdtype):
    class Meta:
        name = "AwardingCriterionID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AwardingCriterionTypeCode(AwardingCriterionTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class AwardingMethodTypeCode(AwardingMethodTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BackOrderAllowedIndicator(BackOrderAllowedIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BackorderQuantity(BackorderQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BackorderReason(BackorderReasonType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BalanceAmount(BalanceAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BalanceBroughtForwardIndicator(BalanceBroughtForwardIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BarcodeSymbologyId(BarcodeSymbologyIdtype):
    class Meta:
        name = "BarcodeSymbologyID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BaseAmount(BaseAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BaseQuantity(BaseQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BaseUnitMeasure(BaseUnitMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BasedOnConsensusIndicator(BasedOnConsensusIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BasicConsumedQuantity(BasicConsumedQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BatchQuantity(BatchQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BestBeforeDate(BestBeforeDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BindingOnBuyerIndicator(BindingOnBuyerIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BirthDate(BirthDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BirthplaceName(BirthplaceNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BlockName(BlockNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BrandName(BrandNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BrokerAssignedId(BrokerAssignedIdtype):
    class Meta:
        name = "BrokerAssignedID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BudgetYearNumeric(BudgetYearNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BuildingName(BuildingNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BuildingNumber(BuildingNumberType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BulkCargoIndicator(BulkCargoIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BusinessClassificationEvidenceId(BusinessClassificationEvidenceIdtype):
    class Meta:
        name = "BusinessClassificationEvidenceID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BusinessIdentityEvidenceId(BusinessIdentityEvidenceIdtype):
    class Meta:
        name = "BusinessIdentityEvidenceID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BuyerEventId(BuyerEventIdtype):
    class Meta:
        name = "BuyerEventID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BuyerProfileUri(BuyerProfileUritype):
    class Meta:
        name = "BuyerProfileURI"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class BuyerReference(BuyerReferenceType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Cv2Id(Cv2Idtype):
    class Meta:
        name = "CV2ID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CalculationExpression(CalculationExpressionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CalculationExpressionCode(CalculationExpressionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CalculationMethodCode(CalculationMethodCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CalculationRate(CalculationRateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CalculationSequenceNumeric(CalculationSequenceNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CallBaseAmount(CallBaseAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CallDate(CallDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CallExtensionAmount(CallExtensionAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CallTime(CallTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CancellationNote(CancellationNoteType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CandidateReductionConstraintIndicator(CandidateReductionConstraintIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CandidateStatement(CandidateStatementType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CanonicalizationMethod(CanonicalizationMethodType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CapabilityTypeCode(CapabilityTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CardChipCode(CardChipCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CardTypeCode(CardTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CargoTypeCode(CargoTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CarrierAssignedId(CarrierAssignedIdtype):
    class Meta:
        name = "CarrierAssignedID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CarrierServiceInstructions(CarrierServiceInstructionsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CatalogueIndicator(CatalogueIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CategoryName(CategoryNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CertificateType(CertificateTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CertificateTypeCode(CertificateTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ChangeConditions(ChangeConditionsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Channel(ChannelType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ChannelCode(ChannelCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CharacterSetCode(CharacterSetCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Characteristics(CharacteristicsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ChargeIndicator(ChargeIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ChargeTotalAmount(ChargeTotalAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ChargeableQuantity(ChargeableQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ChargeableWeightMeasure(ChargeableWeightMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ChildConsignmentQuantity(ChildConsignmentQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ChipApplicationId(ChipApplicationIdtype):
    class Meta:
        name = "ChipApplicationID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CityName(CityNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CitySubdivisionName(CitySubdivisionNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CodeValue(CodeValueType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CollaborationPriorityCode(CollaborationPriorityCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Comment(CommentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CommodityCode(CommodityCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CompanyId(CompanyIdtype):
    class Meta:
        name = "CompanyID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CompanyLegalForm(CompanyLegalFormType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CompanyLegalFormCode(CompanyLegalFormCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CompanyLiquidationStatusCode(CompanyLiquidationStatusCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ComparedValueMeasure(ComparedValueMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ComparisonDataCode(ComparisonDataCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ComparisonDataSourceCode(ComparisonDataSourceCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ComparisonForecastIssueDate(ComparisonForecastIssueDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ComparisonForecastIssueTime(ComparisonForecastIssueTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CompletionIndicator(CompletionIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Condition(ConditionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConditionCode(ConditionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Conditions(ConditionsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConditionsDescription(ConditionsDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsigneeAssignedId(ConsigneeAssignedIdtype):
    class Meta:
        name = "ConsigneeAssignedID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsignmentQuantity(ConsignmentQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsignorAssignedId(ConsignorAssignedIdtype):
    class Meta:
        name = "ConsignorAssignedID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsolidatableIndicator(ConsolidatableIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConstitutionCode(ConstitutionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsumerIncentiveTacticTypeCode(ConsumerIncentiveTacticTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsumerUnitQuantity(ConsumerUnitQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsumersEnergyLevel(ConsumersEnergyLevelType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsumersEnergyLevelCode(ConsumersEnergyLevelCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsumptionEnergyQuantity(ConsumptionEnergyQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsumptionId(ConsumptionIdtype):
    class Meta:
        name = "ConsumptionID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsumptionLevel(ConsumptionLevelType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsumptionLevelCode(ConsumptionLevelCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsumptionReportId(ConsumptionReportIdtype):
    class Meta:
        name = "ConsumptionReportID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsumptionType(ConsumptionTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsumptionTypeCode(ConsumptionTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ConsumptionWaterQuantity(ConsumptionWaterQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ContainerizedIndicator(ContainerizedIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Content(ContentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ContentUnitQuantity(ContentUnitQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ContractFolderId(ContractFolderIdtype):
    class Meta:
        name = "ContractFolderID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ContractName(ContractNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ContractSubdivision(ContractSubdivisionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ContractType(ContractTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ContractTypeCode(ContractTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ContractedCarrierAssignedId(ContractedCarrierAssignedIdtype):
    class Meta:
        name = "ContractedCarrierAssignedID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ContractingSystemCode(ContractingSystemCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CoordinateSystemCode(CoordinateSystemCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CopyIndicator(CopyIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CorporateRegistrationTypeCode(CorporateRegistrationTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CorporateStockAmount(CorporateStockAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CorrectionAmount(CorrectionAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CorrectionType(CorrectionTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CorrectionTypeCode(CorrectionTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CorrectionUnitAmount(CorrectionUnitAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CountrySubentity(CountrySubentityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CountrySubentityCode(CountrySubentityCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CreditLineAmount(CreditLineAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CreditNoteTypeCode(CreditNoteTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CreditedQuantity(CreditedQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CrewQuantity(CrewQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CurrencyCode(CurrencyCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CurrentChargeType(CurrentChargeTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CurrentChargeTypeCode(CurrentChargeTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CustomerAssignedAccountId(CustomerAssignedAccountIdtype):
    class Meta:
        name = "CustomerAssignedAccountID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CustomerReference(CustomerReferenceType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CustomizationId(CustomizationIdtype):
    class Meta:
        name = "CustomizationID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CustomsClearanceServiceInstructions(CustomsClearanceServiceInstructionsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CustomsImportClassifiedIndicator(CustomsImportClassifiedIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CustomsStatusCode(CustomsStatusCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class CustomsTariffQuantity(CustomsTariffQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DamageRemarks(DamageRemarksType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DangerousGoodsApprovedIndicator(DangerousGoodsApprovedIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DataSendingCapability(DataSendingCapabilityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DataSourceCode(DataSourceCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Date(DateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DebitLineAmount(DebitLineAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DebitedQuantity(DebitedQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DeclarationTypeCode(DeclarationTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DeclaredCarriageValueAmount(DeclaredCarriageValueAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DeclaredCustomsValueAmount(DeclaredCustomsValueAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DeclaredForCarriageValueAmount(DeclaredForCarriageValueAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DeclaredStatisticsValueAmount(DeclaredStatisticsValueAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DeliveredQuantity(DeliveredQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DeliveryInstructions(DeliveryInstructionsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DemurrageInstructions(DemurrageInstructionsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Department(DepartmentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Description(DescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DescriptionCode(DescriptionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DespatchAdviceTypeCode(DespatchAdviceTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DifferenceTemperatureReductionQuantity(
    DifferenceTemperatureReductionQuantityType
):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DirectionCode(DirectionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DisplayTacticTypeCode(DisplayTacticTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DispositionCode(DispositionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class District(DistrictType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DocumentCurrencyCode(DocumentCurrencyCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DocumentDescription(DocumentDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DocumentHash(DocumentHashType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DocumentId(DocumentIdtype):
    class Meta:
        name = "DocumentID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DocumentStatusCode(DocumentStatusCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DocumentStatusReasonCode(DocumentStatusReasonCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DocumentStatusReasonDescription(DocumentStatusReasonDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DocumentType(DocumentTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DocumentTypeCode(DocumentTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DocumentationFeeAmount(DocumentationFeeAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DueDate(DueDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DurationMeasure(DurationMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Duty(DutyType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class DutyCode(DutyCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EarliestPickupDate(EarliestPickupDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EarliestPickupTime(EarliestPickupTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EconomicOperatorRegistryUri(EconomicOperatorRegistryUritype):
    class Meta:
        name = "EconomicOperatorRegistryURI"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EffectiveDate(EffectiveDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EffectiveTime(EffectiveTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ElectronicDeviceDescription(ElectronicDeviceDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ElectronicMail(ElectronicMailType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EmbeddedDocumentBinaryObject(EmbeddedDocumentBinaryObjectType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EmergencyProceduresCode(EmergencyProceduresCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EmployeeQuantity(EmployeeQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EncodingCode(EncodingCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EndDate(EndDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EndTime(EndTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EndpointId(EndpointIdtype):
    class Meta:
        name = "EndpointID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EnvironmentalEmissionTypeCode(EnvironmentalEmissionTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EstimatedAmount(EstimatedAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EstimatedConsumedQuantity(EstimatedConsumedQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EstimatedDeliveryDate(EstimatedDeliveryDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EstimatedDeliveryTime(EstimatedDeliveryTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EstimatedDespatchDate(EstimatedDespatchDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EstimatedDespatchTime(EstimatedDespatchTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EstimatedOverallContractAmount(EstimatedOverallContractAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EstimatedOverallContractQuantity(EstimatedOverallContractQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EvaluationCriterionTypeCode(EvaluationCriterionTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class EvidenceTypeCode(EvidenceTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExceptionResolutionCode(ExceptionResolutionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExceptionStatusCode(ExceptionStatusCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExchangeMarketId(ExchangeMarketIdtype):
    class Meta:
        name = "ExchangeMarketID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExclusionReason(ExclusionReasonType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExecutionRequirementCode(ExecutionRequirementCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExemptionReason(ExemptionReasonType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExemptionReasonCode(ExemptionReasonCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExpectedOperatorQuantity(ExpectedOperatorQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExpectedQuantity(ExpectedQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExpenseCode(ExpenseCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExpiryDate(ExpiryDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExpiryTime(ExpiryTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Expression(ExpressionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExpressionCode(ExpressionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ExtendedId(ExtendedIdtype):
    class Meta:
        name = "ExtendedID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Extension(ExtensionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FaceValueAmount(FaceValueAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FamilyName(FamilyNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FeatureTacticTypeCode(FeatureTacticTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FeeAmount(FeeAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FeeDescription(FeeDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FileName(FileNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FinancingInstrumentCode(FinancingInstrumentCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FirstName(FirstNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FirstShipmentAvailibilityDate(FirstShipmentAvailibilityDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Floor(FloorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FollowupContractIndicator(FollowupContractIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ForecastPurposeCode(ForecastPurposeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ForecastTypeCode(ForecastTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FormatCode(FormatCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ForwarderServiceInstructions(ForwarderServiceInstructionsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FreeOfChargeIndicator(FreeOfChargeIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FreeOnBoardValueAmount(FreeOnBoardValueAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FreightForwarderAssignedId(FreightForwarderAssignedIdtype):
    class Meta:
        name = "FreightForwarderAssignedID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FreightRateClassCode(FreightRateClassCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Frequency(FrequencyType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FrozenDocumentIndicator(FrozenDocumentIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FrozenPeriodDaysNumeric(FrozenPeriodDaysNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FullnessIndicationCode(FullnessIndicationCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FullyPaidSharesIndicator(FullyPaidSharesIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FundingProgram(FundingProgramType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class FundingProgramCode(FundingProgramCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class GasPressureQuantity(GasPressureQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class GenderCode(GenderCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class GeneralCargoIndicator(GeneralCargoIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class GovernmentAgreementConstraintIndicator(
    GovernmentAgreementConstraintIndicatorType
):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class GrossTonnageMeasure(GrossTonnageMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class GrossVolumeMeasure(GrossVolumeMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class GrossWeightMeasure(GrossWeightMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class GuaranteeTypeCode(GuaranteeTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class GuaranteedDespatchDate(GuaranteedDespatchDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class GuaranteedDespatchTime(GuaranteedDespatchTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class HandlingCode(HandlingCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class HandlingInstructions(HandlingInstructionsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class HashAlgorithmMethod(HashAlgorithmMethodType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class HaulageInstructions(HaulageInstructionsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class HazardClassId(HazardClassIdtype):
    class Meta:
        name = "HazardClassID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class HazardousCategoryCode(HazardousCategoryCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class HazardousRegulationCode(HazardousRegulationCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class HazardousRiskIndicator(HazardousRiskIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class HeatingType(HeatingTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class HeatingTypeCode(HeatingTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class HigherTenderAmount(HigherTenderAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class HolderName(HolderNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class HumanFoodApprovedIndicator(HumanFoodApprovedIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class HumanFoodIndicator(HumanFoodIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class HumidityPercent(HumidityPercentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Id(Idtype):
    class Meta:
        name = "ID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class IdentificationCode(IdentificationCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class IdentificationId(IdentificationIdtype):
    class Meta:
        name = "IdentificationID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ImmobilizationCertificateId(ImmobilizationCertificateIdtype):
    class Meta:
        name = "ImmobilizationCertificateID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ImportanceCode(ImportanceCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class IndicationIndicator(IndicationIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class IndustryClassificationCode(IndustryClassificationCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Information(InformationType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class InformationUri(InformationUritype):
    class Meta:
        name = "InformationURI"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class InhalationToxicityZoneCode(InhalationToxicityZoneCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class InhouseMail(InhouseMailType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class InspectionMethodCode(InspectionMethodCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class InstallmentDueDate(InstallmentDueDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class InstructionId(InstructionIdtype):
    class Meta:
        name = "InstructionID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class InstructionNote(InstructionNoteType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Instructions(InstructionsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class InsurancePremiumAmount(InsurancePremiumAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class InsuranceValueAmount(InsuranceValueAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class InventoryValueAmount(InventoryValueAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class InvoiceTypeCode(InvoiceTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class InvoicedQuantity(InvoicedQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class InvoicingPartyReference(InvoicingPartyReferenceType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class IssueDate(IssueDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class IssueNumberId(IssueNumberIdtype):
    class Meta:
        name = "IssueNumberID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class IssueTime(IssueTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class IssuerId(IssuerIdtype):
    class Meta:
        name = "IssuerID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ItemClassificationCode(ItemClassificationCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ItemUpdateRequestIndicator(ItemUpdateRequestIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class JobTitle(JobTitleType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class JourneyId(JourneyIdtype):
    class Meta:
        name = "JourneyID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Justification(JustificationType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class JustificationDescription(JustificationDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Keyword(KeywordType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LanguageId(LanguageIdtype):
    class Meta:
        name = "LanguageID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LastRevisionDate(LastRevisionDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LastRevisionTime(LastRevisionTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LatestDeliveryDate(LatestDeliveryDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LatestDeliveryTime(LatestDeliveryTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LatestMeterQuantity(LatestMeterQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LatestMeterReadingDate(LatestMeterReadingDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LatestMeterReadingMethod(LatestMeterReadingMethodType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LatestMeterReadingMethodCode(LatestMeterReadingMethodCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LatestPickupDate(LatestPickupDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LatestPickupTime(LatestPickupTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LatestProposalAcceptanceDate(LatestProposalAcceptanceDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LatestSecurityClearanceDate(LatestSecurityClearanceDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LatitudeDegreesMeasure(LatitudeDegreesMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LatitudeDirectionCode(LatitudeDirectionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LatitudeMinutesMeasure(LatitudeMinutesMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LeadTimeMeasure(LeadTimeMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LegalReference(LegalReferenceType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LegalStatusIndicator(LegalStatusIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LiabilityAmount(LiabilityAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LicensePlateId(LicensePlateIdtype):
    class Meta:
        name = "LicensePlateID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LifeCycleStatusCode(LifeCycleStatusCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LimitationDescription(LimitationDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Line(LineType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LineCountNumeric(LineCountNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LineExtensionAmount(LineExtensionAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LineId(LineIdtype):
    class Meta:
        name = "LineID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LineNumberNumeric(LineNumberNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LineStatusCode(LineStatusCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ListValue(ListValueType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LivestockIndicator(LivestockIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LoadingLengthMeasure(LoadingLengthMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LoadingSequenceId(LoadingSequenceIdtype):
    class Meta:
        name = "LoadingSequenceID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LocaleCode(LocaleCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Location(LocationType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LocationId(LocationIdtype):
    class Meta:
        name = "LocationID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LocationTypeCode(LocationTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Login(LoginType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LogoReferenceId(LogoReferenceIdtype):
    class Meta:
        name = "LogoReferenceID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LongitudeDegreesMeasure(LongitudeDegreesMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LongitudeDirectionCode(LongitudeDirectionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LongitudeMinutesMeasure(LongitudeMinutesMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LossRisk(LossRiskType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LossRiskResponsibilityCode(LossRiskResponsibilityCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LotNumberId(LotNumberIdtype):
    class Meta:
        name = "LotNumberID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LowTendersDescription(LowTendersDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LowerOrangeHazardPlacardId(LowerOrangeHazardPlacardIdtype):
    class Meta:
        name = "LowerOrangeHazardPlacardID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class LowerTenderAmount(LowerTenderAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MandateTypeCode(MandateTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ManufactureDate(ManufactureDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ManufactureTime(ManufactureTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MarkAttention(MarkAttentionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MarkAttentionIndicator(MarkAttentionIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MarkCare(MarkCareType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MarkCareIndicator(MarkCareIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MarketValueAmount(MarketValueAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MarkingId(MarkingIdtype):
    class Meta:
        name = "MarkingID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MathematicOperatorCode(MathematicOperatorCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MaximumAdvertisementAmount(MaximumAdvertisementAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MaximumAmount(MaximumAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MaximumBackorderQuantity(MaximumBackorderQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MaximumCopiesNumeric(MaximumCopiesNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MaximumMeasure(MaximumMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MaximumNumberNumeric(MaximumNumberNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MaximumOperatorQuantity(MaximumOperatorQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MaximumOrderQuantity(MaximumOrderQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MaximumPaidAmount(MaximumPaidAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MaximumPaymentInstructionsNumeric(MaximumPaymentInstructionsNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MaximumPercent(MaximumPercentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MaximumQuantity(MaximumQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MaximumValue(MaximumValueType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MaximumVariantQuantity(MaximumVariantQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Measure(MeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MedicalFirstAidGuideCode(MedicalFirstAidGuideCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MeterConstant(MeterConstantType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MeterConstantCode(MeterConstantCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MeterName(MeterNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MeterNumber(MeterNumberType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MeterReadingComments(MeterReadingCommentsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MeterReadingType(MeterReadingTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MeterReadingTypeCode(MeterReadingTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MiddleName(MiddleNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MimeCode(MimeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MinimumAmount(MinimumAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MinimumBackorderQuantity(MinimumBackorderQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MinimumImprovementBid(MinimumImprovementBidType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MinimumInventoryQuantity(MinimumInventoryQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MinimumMeasure(MinimumMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MinimumNumberNumeric(MinimumNumberNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MinimumOrderQuantity(MinimumOrderQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MinimumPercent(MinimumPercentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MinimumQuantity(MinimumQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MinimumValue(MinimumValueType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MiscellaneousEventTypeCode(MiscellaneousEventTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ModelName(ModelNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MonetaryScope(MonetaryScopeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MovieTitle(MovieTitleType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MultipleOrderQuantity(MultipleOrderQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class MultiplierFactorNumeric(MultiplierFactorNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Name(NameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class NameCode(NameCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class NameSuffix(NameSuffixType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class NationalityId(NationalityIdtype):
    class Meta:
        name = "NationalityID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class NatureCode(NatureCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class NegotiationDescription(NegotiationDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class NetNetWeightMeasure(NetNetWeightMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class NetTonnageMeasure(NetTonnageMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class NetVolumeMeasure(NetVolumeMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class NetWeightMeasure(NetWeightMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class NetworkId(NetworkIdtype):
    class Meta:
        name = "NetworkID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class NominationDate(NominationDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class NominationTime(NominationTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class NormalTemperatureReductionQuantity(NormalTemperatureReductionQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Note(NoteType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class NotificationTypeCode(NotificationTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OccurrenceDate(OccurrenceDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OccurrenceTime(OccurrenceTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OnCarriageIndicator(OnCarriageIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OneTimeChargeType(OneTimeChargeTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OneTimeChargeTypeCode(OneTimeChargeTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OntologyUri(OntologyUritype):
    class Meta:
        name = "OntologyURI"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OpenTenderId(OpenTenderIdtype):
    class Meta:
        name = "OpenTenderID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OperatingYearsQuantity(OperatingYearsQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OptionalLineItemIndicator(OptionalLineItemIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OptionsDescription(OptionsDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OrderIntervalDaysNumeric(OrderIntervalDaysNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OrderQuantityIncrementNumeric(OrderQuantityIncrementNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OrderResponseCode(OrderResponseCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OrderTypeCode(OrderTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OrderableIndicator(OrderableIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OrderableUnit(OrderableUnitType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OrderableUnitFactorRate(OrderableUnitFactorRateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OrganizationDepartment(OrganizationDepartmentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OriginalContractingSystemId(OriginalContractingSystemIdtype):
    class Meta:
        name = "OriginalContractingSystemID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OriginalJobId(OriginalJobIdtype):
    class Meta:
        name = "OriginalJobID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OtherConditionsIndicator(OtherConditionsIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OtherInstruction(OtherInstructionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OtherName(OtherNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OutstandingQuantity(OutstandingQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OutstandingReason(OutstandingReasonType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OversupplyQuantity(OversupplyQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class OwnerTypeCode(OwnerTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PackLevelCode(PackLevelCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PackQuantity(PackQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PackSizeNumeric(PackSizeNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PackageLevelCode(PackageLevelCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PackagingTypeCode(PackagingTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PackingCriteriaCode(PackingCriteriaCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PackingMaterial(PackingMaterialType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaidAmount(PaidAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaidDate(PaidDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaidTime(PaidTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ParentDocumentId(ParentDocumentIdtype):
    class Meta:
        name = "ParentDocumentID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ParentDocumentLineReferenceId(ParentDocumentLineReferenceIdtype):
    class Meta:
        name = "ParentDocumentLineReferenceID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ParentDocumentTypeCode(ParentDocumentTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ParentDocumentVersionId(ParentDocumentVersionIdtype):
    class Meta:
        name = "ParentDocumentVersionID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PartPresentationCode(PartPresentationCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PartecipationPercent(PartecipationPercentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PartialDeliveryIndicator(PartialDeliveryIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ParticipationPercent(ParticipationPercentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PartyCapacityAmount(PartyCapacityAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PartyType(PartyTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PartyTypeCode(PartyTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PassengerQuantity(PassengerQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Password(PasswordType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PayPerView(PayPerViewType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PayableAlternativeAmount(PayableAlternativeAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PayableAmount(PayableAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PayableRoundingAmount(PayableRoundingAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PayerReference(PayerReferenceType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaymentAlternativeCurrencyCode(PaymentAlternativeCurrencyCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaymentChannelCode(PaymentChannelCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaymentCurrencyCode(PaymentCurrencyCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaymentDescription(PaymentDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaymentDueDate(PaymentDueDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaymentFrequencyCode(PaymentFrequencyCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaymentId(PaymentIdtype):
    class Meta:
        name = "PaymentID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaymentMeansCode(PaymentMeansCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaymentMeansId(PaymentMeansIdtype):
    class Meta:
        name = "PaymentMeansID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaymentNote(PaymentNoteType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaymentOrderReference(PaymentOrderReferenceType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaymentPercent(PaymentPercentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaymentPurposeCode(PaymentPurposeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PaymentTermsDetailsUri(PaymentTermsDetailsUritype):
    class Meta:
        name = "PaymentTermsDetailsURI"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PenaltyAmount(PenaltyAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PenaltySurchargePercent(PenaltySurchargePercentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PerUnitAmount(PerUnitAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Percent(PercentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PerformanceMetricTypeCode(PerformanceMetricTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PerformanceValueQuantity(PerformanceValueQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PerformingCarrierAssignedId(PerformingCarrierAssignedIdtype):
    class Meta:
        name = "PerformingCarrierAssignedID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PersonalSituation(PersonalSituationType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PhoneNumber(PhoneNumberType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PlacardEndorsement(PlacardEndorsementType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PlacardNotation(PlacardNotationType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PlannedDate(PlannedDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PlotIdentification(PlotIdentificationType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PositionCode(PositionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PostEventNotificationDurationMeasure(PostEventNotificationDurationMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PostalZone(PostalZoneType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Postbox(PostboxType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PowerIndicator(PowerIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PreCarriageIndicator(PreCarriageIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PreEventNotificationDurationMeasure(PreEventNotificationDurationMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PreferenceCriterionCode(PreferenceCriterionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PrepaidAmount(PrepaidAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PrepaidIndicator(PrepaidIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PrepaidPaymentReferenceId(PrepaidPaymentReferenceIdtype):
    class Meta:
        name = "PrepaidPaymentReferenceID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PreviousCancellationReasonCode(PreviousCancellationReasonCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PreviousJobId(PreviousJobIdtype):
    class Meta:
        name = "PreviousJobID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PreviousMeterQuantity(PreviousMeterQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PreviousMeterReadingDate(PreviousMeterReadingDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PreviousMeterReadingMethod(PreviousMeterReadingMethodType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PreviousMeterReadingMethodCode(PreviousMeterReadingMethodCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PreviousVersionId(PreviousVersionIdtype):
    class Meta:
        name = "PreviousVersionID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PriceAmount(PriceAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PriceChangeReason(PriceChangeReasonType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PriceEvaluationCode(PriceEvaluationCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PriceRevisionFormulaDescription(PriceRevisionFormulaDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PriceType(PriceTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PriceTypeCode(PriceTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PricingCurrencyCode(PricingCurrencyCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PricingUpdateRequestIndicator(PricingUpdateRequestIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PrimaryAccountNumberId(PrimaryAccountNumberIdtype):
    class Meta:
        name = "PrimaryAccountNumberID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PrintQualifier(PrintQualifierType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Priority(PriorityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PrivacyCode(PrivacyCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PrizeDescription(PrizeDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PrizeIndicator(PrizeIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ProcedureCode(ProcedureCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ProcessDescription(ProcessDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ProcessReason(ProcessReasonType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ProcessReasonCode(ProcessReasonCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ProcurementSubTypeCode(ProcurementSubTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ProcurementTypeCode(ProcurementTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ProductTraceId(ProductTraceIdtype):
    class Meta:
        name = "ProductTraceID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ProfileExecutionId(ProfileExecutionIdtype):
    class Meta:
        name = "ProfileExecutionID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ProfileId(ProfileIdtype):
    class Meta:
        name = "ProfileID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ProfileStatusCode(ProfileStatusCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ProgressPercent(ProgressPercentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PromotionalEventTypeCode(PromotionalEventTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ProviderTypeCode(ProviderTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PublishAwardIndicator(PublishAwardIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Purpose(PurposeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class PurposeCode(PurposeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class QualityControlCode(QualityControlCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Quantity(QuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class QuantityDiscrepancyCode(QuantityDiscrepancyCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RadioCallSignId(RadioCallSignIdtype):
    class Meta:
        name = "RadioCallSignID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RailCarId(RailCarIdtype):
    class Meta:
        name = "RailCarID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Rank(RankType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Rate(RateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReceiptAdviceTypeCode(ReceiptAdviceTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReceivedDate(ReceivedDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReceivedElectronicTenderQuantity(ReceivedElectronicTenderQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReceivedForeignTenderQuantity(ReceivedForeignTenderQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReceivedQuantity(ReceivedQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReceivedTenderQuantity(ReceivedTenderQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Reference(ReferenceType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReferenceDate(ReferenceDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReferenceEventCode(ReferenceEventCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReferenceId(ReferenceIdtype):
    class Meta:
        name = "ReferenceID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReferenceTime(ReferenceTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReferencedConsignmentId(ReferencedConsignmentIdtype):
    class Meta:
        name = "ReferencedConsignmentID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RefrigeratedIndicator(RefrigeratedIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RefrigerationOnIndicator(RefrigerationOnIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Region(RegionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RegisteredDate(RegisteredDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RegisteredTime(RegisteredTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RegistrationDate(RegistrationDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RegistrationExpirationDate(RegistrationExpirationDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RegistrationId(RegistrationIdtype):
    class Meta:
        name = "RegistrationID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RegistrationName(RegistrationNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RegistrationNationality(RegistrationNationalityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RegistrationNationalityId(RegistrationNationalityIdtype):
    class Meta:
        name = "RegistrationNationalityID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RegulatoryDomain(RegulatoryDomainType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RejectActionCode(RejectActionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RejectReason(RejectReasonType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RejectReasonCode(RejectReasonCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RejectedQuantity(RejectedQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RejectionNote(RejectionNoteType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReleaseId(ReleaseIdtype):
    class Meta:
        name = "ReleaseID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReliabilityPercent(ReliabilityPercentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Remarks(RemarksType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReminderSequenceNumeric(ReminderSequenceNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReminderTypeCode(ReminderTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReplenishmentOwnerDescription(ReplenishmentOwnerDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RequestForQuotationLineId(RequestForQuotationLineIdtype):
    class Meta:
        name = "RequestForQuotationLineID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RequestedDeliveryDate(RequestedDeliveryDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RequestedDespatchDate(RequestedDespatchDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RequestedDespatchTime(RequestedDespatchTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RequestedInvoiceCurrencyCode(RequestedInvoiceCurrencyCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RequestedPublicationDate(RequestedPublicationDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RequiredCurriculaIndicator(RequiredCurriculaIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RequiredCustomsId(RequiredCustomsIdtype):
    class Meta:
        name = "RequiredCustomsID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RequiredDeliveryDate(RequiredDeliveryDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RequiredDeliveryTime(RequiredDeliveryTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RequiredFeeAmount(RequiredFeeAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ResidenceType(ResidenceTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ResidenceTypeCode(ResidenceTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ResidentOccupantsNumeric(ResidentOccupantsNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Resolution(ResolutionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ResolutionCode(ResolutionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ResolutionDate(ResolutionDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ResolutionTime(ResolutionTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ResponseCode(ResponseCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ResponseDate(ResponseDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ResponseTime(ResponseTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RetailEventName(RetailEventNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RetailEventStatusCode(RetailEventStatusCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReturnabilityIndicator(ReturnabilityIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReturnableMaterialIndicator(ReturnableMaterialIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ReturnableQuantity(ReturnableQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RevisedForecastLineId(RevisedForecastLineIdtype):
    class Meta:
        name = "RevisedForecastLineID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RevisionDate(RevisionDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RevisionStatusCode(RevisionStatusCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RevisionTime(RevisionTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RoamingPartnerName(RoamingPartnerNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RoleCode(RoleCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RoleDescription(RoleDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Room(RoomType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class RoundingAmount(RoundingAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SalesOrderId(SalesOrderIdtype):
    class Meta:
        name = "SalesOrderID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SalesOrderLineId(SalesOrderLineIdtype):
    class Meta:
        name = "SalesOrderLineID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SchemeUri(SchemeUritype):
    class Meta:
        name = "SchemeURI"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SealIssuerTypeCode(SealIssuerTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SealStatusCode(SealStatusCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SealingPartyType(SealingPartyTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SecurityClassificationCode(SecurityClassificationCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SecurityId(SecurityIdtype):
    class Meta:
        name = "SecurityID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SellerEventId(SellerEventIdtype):
    class Meta:
        name = "SellerEventID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SequenceId(SequenceIdtype):
    class Meta:
        name = "SequenceID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SequenceNumberId(SequenceNumberIdtype):
    class Meta:
        name = "SequenceNumberID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SequenceNumeric(SequenceNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SerialId(SerialIdtype):
    class Meta:
        name = "SerialID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ServiceInformationPreferenceCode(ServiceInformationPreferenceCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ServiceName(ServiceNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ServiceNumberCalled(ServiceNumberCalledType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ServiceType(ServiceTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ServiceTypeCode(ServiceTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SettlementDiscountAmount(SettlementDiscountAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SettlementDiscountPercent(SettlementDiscountPercentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SharesNumberQuantity(SharesNumberQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ShippingMarks(ShippingMarksType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ShippingOrderId(ShippingOrderIdtype):
    class Meta:
        name = "ShippingOrderID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ShippingPriorityLevelCode(ShippingPriorityLevelCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ShipsRequirements(ShipsRequirementsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ShortQuantity(ShortQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ShortageActionCode(ShortageActionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SignatureId(SignatureIdtype):
    class Meta:
        name = "SignatureID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SignatureMethod(SignatureMethodType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SizeTypeCode(SizeTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SoleProprietorshipIndicator(SoleProprietorshipIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SourceCurrencyBaseRate(SourceCurrencyBaseRateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SourceCurrencyCode(SourceCurrencyCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SourceForecastIssueDate(SourceForecastIssueDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SourceForecastIssueTime(SourceForecastIssueTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SourceValueMeasure(SourceValueMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SpecialInstructions(SpecialInstructionsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SpecialSecurityIndicator(SpecialSecurityIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SpecialServiceInstructions(SpecialServiceInstructionsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SpecialTerms(SpecialTermsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SpecialTransportRequirements(SpecialTransportRequirementsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SpecificationId(SpecificationIdtype):
    class Meta:
        name = "SpecificationID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SpecificationTypeCode(SpecificationTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SplitConsignmentIndicator(SplitConsignmentIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class StartDate(StartDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class StartTime(StartTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class StatementTypeCode(StatementTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class StatusAvailableIndicator(StatusAvailableIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class StatusCode(StatusCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class StatusReason(StatusReasonType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class StatusReasonCode(StatusReasonCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class StreetName(StreetNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SubcontractingConditionsCode(SubcontractingConditionsCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SubmissionDate(SubmissionDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SubmissionDueDate(SubmissionDueDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SubmissionMethodCode(SubmissionMethodCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SubscriberId(SubscriberIdtype):
    class Meta:
        name = "SubscriberID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SubscriberType(SubscriberTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SubscriberTypeCode(SubscriberTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SubstitutionStatusCode(SubstitutionStatusCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SuccessiveSequenceId(SuccessiveSequenceIdtype):
    class Meta:
        name = "SuccessiveSequenceID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SummaryDescription(SummaryDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SupplierAssignedAccountId(SupplierAssignedAccountIdtype):
    class Meta:
        name = "SupplierAssignedAccountID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class SupplyChainActivityTypeCode(SupplyChainActivityTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TareWeightMeasure(TareWeightMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TargetCurrencyBaseRate(TargetCurrencyBaseRateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TargetCurrencyCode(TargetCurrencyCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TargetInventoryQuantity(TargetInventoryQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TargetServicePercent(TargetServicePercentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TariffClassCode(TariffClassCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TariffCode(TariffCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TariffDescription(TariffDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TaxAmount(TaxAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TaxCurrencyCode(TaxCurrencyCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TaxEnergyAmount(TaxEnergyAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TaxEnergyBalanceAmount(TaxEnergyBalanceAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TaxEnergyOnAccountAmount(TaxEnergyOnAccountAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TaxEvidenceIndicator(TaxEvidenceIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TaxExclusiveAmount(TaxExclusiveAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TaxExemptionReason(TaxExemptionReasonType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TaxExemptionReasonCode(TaxExemptionReasonCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TaxIncludedIndicator(TaxIncludedIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TaxInclusiveAmount(TaxInclusiveAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TaxLevelCode(TaxLevelCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TaxPointDate(TaxPointDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TaxTypeCode(TaxTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TaxableAmount(TaxableAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TechnicalCommitteeDescription(TechnicalCommitteeDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TechnicalName(TechnicalNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TelecommunicationsServiceCall(TelecommunicationsServiceCallType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TelecommunicationsServiceCallCode(TelecommunicationsServiceCallCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TelecommunicationsServiceCategory(TelecommunicationsServiceCategoryType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TelecommunicationsServiceCategoryCode(TelecommunicationsServiceCategoryCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TelecommunicationsSupplyType(TelecommunicationsSupplyTypeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TelecommunicationsSupplyTypeCode(TelecommunicationsSupplyTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Telefax(TelefaxType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Telephone(TelephoneType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TenderEnvelopeId(TenderEnvelopeIdtype):
    class Meta:
        name = "TenderEnvelopeID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TenderEnvelopeTypeCode(TenderEnvelopeTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TenderResultCode(TenderResultCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TenderTypeCode(TenderTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TendererRequirementTypeCode(TendererRequirementTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TendererRoleCode(TendererRoleCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TestMethod(TestMethodType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Text(TextType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ThirdPartyPayerIndicator(ThirdPartyPayerIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ThresholdAmount(ThresholdAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ThresholdQuantity(ThresholdQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ThresholdValueComparisonCode(ThresholdValueComparisonCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TierRange(TierRangeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TierRatePercent(TierRatePercentType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TimeAmount(TimeAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TimeDeltaDaysQuantity(TimeDeltaDaysQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TimeFrequencyCode(TimeFrequencyCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TimezoneOffset(TimezoneOffsetType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TimingComplaint(TimingComplaintType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TimingComplaintCode(TimingComplaintCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Title(TitleType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ToOrderIndicator(ToOrderIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TotalAmount(TotalAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TotalBalanceAmount(TotalBalanceAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TotalConsumedQuantity(TotalConsumedQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TotalCreditAmount(TotalCreditAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TotalDebitAmount(TotalDebitAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TotalDeliveredQuantity(TotalDeliveredQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TotalGoodsItemQuantity(TotalGoodsItemQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TotalInvoiceAmount(TotalInvoiceAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TotalMeteredQuantity(TotalMeteredQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TotalPackageQuantity(TotalPackageQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TotalPackagesQuantity(TotalPackagesQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TotalPaymentAmount(TotalPaymentAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TotalTaskAmount(TotalTaskAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TotalTaxAmount(TotalTaxAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TotalTransportHandlingUnitQuantity(TotalTransportHandlingUnitQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TraceId(TraceIdtype):
    class Meta:
        name = "TraceID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TrackingDeviceCode(TrackingDeviceCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TrackingId(TrackingIdtype):
    class Meta:
        name = "TrackingID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TradeItemPackingLabelingTypeCode(TradeItemPackingLabelingTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TradeServiceCode(TradeServiceCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TradingRestrictions(TradingRestrictionsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TrainId(TrainIdtype):
    class Meta:
        name = "TrainID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransactionCurrencyTaxAmount(TransactionCurrencyTaxAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransitDirectionCode(TransitDirectionCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportAuthorizationCode(TransportAuthorizationCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportEmergencyCardCode(TransportEmergencyCardCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportEquipmentTypeCode(TransportEquipmentTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportEventTypeCode(TransportEventTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportExecutionPlanReferenceId(TransportExecutionPlanReferenceIdtype):
    class Meta:
        name = "TransportExecutionPlanReferenceID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportExecutionStatusCode(TransportExecutionStatusCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportHandlingUnitTypeCode(TransportHandlingUnitTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportMeansTypeCode(TransportMeansTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportModeCode(TransportModeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportServiceCode(TransportServiceCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportServiceProviderRemarks(TransportServiceProviderRemarksType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportServiceProviderSpecialTerms(TransportServiceProviderSpecialTermsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportUserRemarks(TransportUserRemarksType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportUserSpecialTerms(TransportUserSpecialTermsType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportationServiceDescription(TransportationServiceDescriptionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportationServiceDetailsUri(TransportationServiceDetailsUritype):
    class Meta:
        name = "TransportationServiceDetailsURI"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TransportationStatusTypeCode(TransportationStatusTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class TypeCode(TypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class UblversionId(UblversionIdtype):
    class Meta:
        name = "UBLVersionID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Undgcode(UndgcodeType):
    class Meta:
        name = "UNDGCode"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Uri(Uritype):
    class Meta:
        name = "URI"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Uuid(Uuidtype):
    class Meta:
        name = "UUID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class UnknownPriceIndicator(UnknownPriceIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class UpperOrangeHazardPlacardId(UpperOrangeHazardPlacardIdtype):
    class Meta:
        name = "UpperOrangeHazardPlacardID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class UrgencyCode(UrgencyCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class UtilityStatementTypeCode(UtilityStatementTypeCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ValidateProcess(ValidateProcessType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ValidateTool(ValidateToolType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ValidateToolVersion(ValidateToolVersionType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ValidationDate(ValidationDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ValidationResultCode(ValidationResultCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ValidationTime(ValidationTimeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ValidatorId(ValidatorIdtype):
    class Meta:
        name = "ValidatorID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ValidityStartDate(ValidityStartDateType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Value(ValueType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ValueAmount(ValueAmountType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ValueMeasure(ValueMeasureType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ValueQualifier(ValueQualifierType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class ValueQuantity(ValueQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class VarianceQuantity(VarianceQuantityType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class VariantConstraintIndicator(VariantConstraintIndicatorType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class VariantId(VariantIdtype):
    class Meta:
        name = "VariantID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class VersionId(VersionIdtype):
    class Meta:
        name = "VersionID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class VesselId(VesselIdtype):
    class Meta:
        name = "VesselID"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class VesselName(VesselNameType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class WarrantyInformation(WarrantyInformationType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class WebsiteUri(WebsiteUritype):
    class Meta:
        name = "WebsiteURI"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class WeekDayCode(WeekDayCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Weight(WeightType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class WeightNumeric(WeightNumericType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class WeightingAlgorithmCode(WeightingAlgorithmCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class WorkPhase(WorkPhaseType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class WorkPhaseCode(WorkPhaseCodeType):
    class Meta:
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)


class Xpath(XpathType):
    class Meta:
        name = "XPath"
        namespace = (
            "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        )

    model_config = ConfigDict(defer_build=True)
