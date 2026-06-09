"""Telegram Stars checkout: invoice → pre-checkout → fulfilment."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from keyboards import inline
from keyboards.callbacks import BuyCB, MenuCB
from services import access_service, payment_service, pricing, user_service
from utils import texts
from utils.telegram import safe_edit

router = Router(name="payments")


@router.callback_query(MenuCB.filter(F.action == "pro"))
async def open_offer(query: CallbackQuery, state: FSMContext) -> None:
    """The sales / offer screen — outcome promise, perks, social proof, price."""
    await state.clear()
    user = await user_service.get_user(query.from_user.id)
    await safe_edit(query.message, texts.offer(access_service.is_pro(user)), inline.offer(access_service.is_pro(user)))
    await query.answer()


@router.callback_query(BuyCB.filter())
async def start_purchase(query: CallbackQuery, callback_data: BuyCB) -> None:
    product = pricing.get(callback_data.product)
    if product is None:
        await query.answer()
        return
    if not payment_service.enabled():
        await query.answer(texts.PAYMENTS_OFF_ALERT, show_alert=True)
        return
    await query.message.answer_invoice(
        title=product.title,
        description=product.blurb,
        payload=product.id,
        provider_token="",      # empty ⇒ Telegram Stars
        currency="XTR",
        prices=[LabeledPrice(label=product.title, amount=product.stars)],
    )
    await query.answer()


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_q: PreCheckoutQuery) -> None:
    # Approve the payment; last chance to reject (e.g. out of stock).
    await pre_checkout_q.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message) -> None:
    payment = message.successful_payment
    product = await payment_service.fulfill(
        message.from_user.id, payment.invoice_payload, payment.telegram_payment_charge_id
    )
    if product is None:
        await message.answer(texts.PURCHASE_UNKNOWN, reply_markup=inline.back_to_menu())
        return
    await message.answer(texts.purchase_success(product), reply_markup=inline.after_purchase())
