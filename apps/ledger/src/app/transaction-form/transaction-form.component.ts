import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormGroup, FormBuilder, Validators, AbstractControl } from '@angular/forms';
import { Router, ActivatedRoute, Params } from '@angular/router';
import { formatDate } from '@angular/common'
import { Transaction } from '../models/transaction';
import { Account } from '../models/account';
import { LedgerService } from '../ledger.service';
import { Observable, switchMap } from 'rxjs';
import { isObject, omitBy } from "lodash-es"

function dateRange(group: FormGroup): {[key: string]: boolean} | null {
    const occurredOn = group.get('occurred_on')!.value;
    const clearedOn = group.get('cleared_on')!.value;

    if (!clearedOn) {
        return null;
    }

    if (clearedOn >= occurredOn) {
        return null;
    }

    return { 'daterange': true }

}
@Component({
  selector: 'app-transaction-form',
  templateUrl: './transaction-form.component.html',
  styleUrls: ['./transaction-form.component.css']
})
export class TransactionFormComponent {
    transactionForm!: FormGroup;
    transaction: Transaction | undefined;
    errorMessage = '';
    datesExpanded = false;
    singularResourceName: string;

    constructor(
        private router: Router,
        private route: ActivatedRoute,
        private formBuilder: FormBuilder,
        private ledgerService: LedgerService
    ) {
        this.singularResourceName = 'transaction';
    }

    ngOnInit(): void {
        const id = Number(this.route.snapshot.paramMap.get('id') || 0)

        this.transactionForm = this.formBuilder.group({
            account_id: ['', {validators:Validators.required}],
            payee: ['', {updatedOn: 'blur', validators: Validators.required}],
            amount: ['', {updatedOn: 'blur', validators: [Validators.required, Validators.pattern('[0-9.]+'), Validators.min(0.01)]}],
            dates: this.formBuilder.group({
                occurred_on: this.today(),
                cleared_on: '',
            }, {validators: dateRange}),
            note: ['', {updateOn: 'blur'}],
        });

        this.ledgerService.getTransaction(id).subscribe(
            (transaction: Transaction) => this.populate(transaction),
            (err: any) => console.log(err),
            () => console.log('All done getting transaction'),
        );
    }

    ngOnDestory(): void {
    }

    get accountId() { return this.transactionForm.controls['account_id'] }
    get payee() { return this.transactionForm.controls['payee'] }
    get amount() { return this.transactionForm.controls['amount'] }
    get dates() { return this.transactionForm.controls['dates'] as FormGroup }
    get occurredOn() { return this.dates.controls['occurred_on'] }
    get clearedOn() { return this.dates.controls['cleared_on'] }
    get note() { return this.transactionForm.controls['note'] }


    today() {
        return formatDate(new Date(), 'yyyy-MM-dd', 'en');
    }

    populate(transaction: Transaction) {
        this.transactionForm.reset();

        this.transactionForm.patchValue({
            account_id: transaction.account?.uid,
            payee: transaction.payee,
            amount: transaction.amount,
            dates: {
                occurred_on: transaction.occurred_on,
                cleared_on: transaction.cleared_on,
            },
            note: transaction.note,
        });

        if (transaction.account.closed_on) {
            this.accountId.disable();
        } else {
            this.accountId.enable();
        }

        this.transaction = transaction;
        this.datesExpanded = (transaction.cleared_on !== null);
    }

    toggleTransactionCleared(event: Event) {
        this.datesExpanded = (event.target as HTMLInputElement).checked;
        this.transactionForm.markAsDirty();

        this.dates.patchValue({
            cleared_on: (this.datesExpanded)? this.today() : null,
        });
    }

    changeAccount(account: Account) {
        this.transactionForm.patchValue({
            account_id: account.uid,
        });
    }

    save(): void {
        if (!this.transactionForm.valid) {
            this.errorMessage = 'Cannot save your changes because the form is incomplete.';
            return;
        }

        if (!this.transactionForm.dirty) {
            this.errorMessage = 'Cannot save your changes because nothing has changed.';
            return;
        }

        const outboundTransaction: Transaction = {
            ...this.transaction,
            ...omitBy(this.transactionForm.value, (v, _) => {
                return isObject(v);
            }),
            'account_id': this.accountId.value,
            ...this.dates.value,
        };

        if (outboundTransaction.uid === 0) {
            this.ledgerService.addTransaction(outboundTransaction).subscribe(
                () => this.saved(),
                (err) => this.errorMessage = err,
            );
        }

        if (outboundTransaction.uid > 0) {
            this.ledgerService.updateTransaction(outboundTransaction).subscribe(
                () => this.saved(),
                (err) => this.errorMessage = err,
            );
        }
    }

    saved() {
        this.transactionForm.reset();
        this.router.navigate(['/transactions']);
    }

    deleted() {
        this.transactionForm.reset();
        this.router.navigate(['/transactions']);
    }

    canDelete(): boolean {
        if (!this.transaction) {
            return false;
        }
        return this.transaction.uid > 0;
    }


    deleteTransaction() {
        if (!this.transaction) {
            return;
        }

        this.ledgerService.deleteTransaction(this.transaction.uid).subscribe(
            () => this.deleted(),
            (err) => this.errorMessage = err,
        );
    }
}
