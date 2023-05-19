import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormArray, FormGroup, FormBuilder, Validators, AbstractControl } from '@angular/forms';
import { Router, ActivatedRoute, Params } from '@angular/router';
import { formatDate } from '@angular/common'
import { TransactionPrimitive } from '../types/transactionPrimitive';
import { Transaction } from '../models/transaction';
import { TransactionList } from '../types/transactionList';
import { Account } from '../models/account';
import { LedgerService } from '../ledger.service';
import { Observable, Subject, switchMap, debounceTime, distinctUntilChanged, filter } from 'rxjs';
import { isObject, omitBy } from "lodash-es"
import { MoneyPipe } from '../money.pipe';

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
    autocompletedFrom: Transaction | null;

    constructor(
        private router: Router,
        private route: ActivatedRoute,
        private formBuilder: FormBuilder,
        private ledgerService: LedgerService,
        private moneyPipe: MoneyPipe

    ) {
        this.singularResourceName = 'transaction';
        this.autocompletedFrom = null;
    }

    ngOnInit(): void {
        const id = Number(this.route.snapshot.paramMap.get('id') || 0)

        this.transactionForm = this.formBuilder.group({
            account_id: ['', {validators:Validators.required}],
            payee: ['', {validators: Validators.required}],
            amount: ['', {updatedOn: 'blur', validators: [Validators.required, Validators.pattern('[0-9.]+'), Validators.min(0.01)]}],
            dates: this.formBuilder.group({
                occurred_on: this.today(),
                cleared_on: '',
            }, {validators: dateRange}),
            tags: this.formBuilder.array([]),
            note: ['', {updateOn: 'blur'}],
        });

        this.ledgerService.getTransaction(id).subscribe(
            (transaction: Transaction) => this.populate(transaction),
            (err: any) => console.log(err),
            () => console.log('All done getting transaction'),
        );

        if (id === 0) {
            this.payee.valueChanges.pipe(
                filter(value => value && value.length > 2),
                debounceTime(1000),
                distinctUntilChanged(),
                switchMap(payee => this.ledgerService.autocompletePayee(payee)),
            ).subscribe((result => this.autocomplete(result)));
        }
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
    get tags() { return this.transactionForm.get('tags') as FormArray }

    autocomplete(searchResult: TransactionList) {
        if (searchResult.count !== 1) {
            this.autocompletedFrom = null;
            return;
        }

        const transaction = new Transaction(searchResult.transactions[0]);
        this.transactionForm.patchValue({
            account_id: transaction.account.uid,
            payee: transaction.payee,
            amount: this.moneyPipe.transform(transaction.amount, 'plain'),
            note: transaction.note,
        });
        this.autocompletedFrom = transaction;
    }

    tagFieldPush(value = '') {
        this.tags.push(this.formBuilder.control(value));
        this.transactionForm.markAsDirty();
    }

    tagFieldPop() {
        this.tags.removeAt(-1);
        this.transactionForm.markAsDirty();
    }

    today() {
        return formatDate(new Date(), 'yyyy-MM-dd', 'en');
    }

    populate(transaction: Transaction) {
        this.transactionForm.reset();

        this.transactionForm.patchValue({
            payee: transaction.payee,
            amount: this.moneyPipe.transform(transaction.amount, 'plain'),
            account_id: transaction.account.uid,
            dates: {
                occurred_on: transaction.occurredOnYMD(),
                cleared_on: transaction.clearedOnYMD(),
            },
            note: transaction.note,
        });

        while (this.tags.controls.length < transaction.tags.length) {
            this.tagFieldPush();
        }

        this.tags.patchValue(transaction.tags);

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

        const primitive: TransactionPrimitive = {
            'uid': this.transaction!.uid,
            'account_id': this.accountId.value,
            'payee': this.payee.value,
            'amount': this.amount.value * 100,
            'occurred_on': this.occurredOn.value,
            'cleared_on': this.clearedOn.value,
            'note': this.note.value,
            'tags': this.tags.value,
        };

        if (primitive.uid === 0) {
            this.ledgerService.addTransaction(primitive).subscribe(
                () => this.saved(),
                (err) => this.errorMessage = err,
            );
        }

        if (primitive.uid > 0) {
            this.ledgerService.updateTransaction(primitive).subscribe(
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
