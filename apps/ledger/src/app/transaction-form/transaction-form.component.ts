import { Component, OnInit } from '@angular/core';
import { FormArray, FormGroup, FormControl, FormBuilder, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { formatDate } from '@angular/common'
import { Transaction } from '../models/transaction';
import { TransactionList } from '../types/TransactionList';
import { Account } from '../models/account';
import { LedgerService } from '../ledger.service';
import { switchMap, debounceTime, filter } from 'rxjs';
import { MoneyPipe } from '../money.pipe';

function atLeastOneAccount(group: AbstractControl): ValidationErrors | null {
    const account = group.get('account')!;
    const destination = group.get('destination')!;

    if (account.pristine && destination.pristine) {
        return null;
    }

    if (account.value || destination.value) {
        return null;
    }

    return { 'atLeastOneAccount': true }
}

function dateRange(group: AbstractControl): ValidationErrors | null {
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
  selector: 'ledger-transaction-form',
  templateUrl: './transaction-form.component.html',
  styleUrls: ['./transaction-form.component.css']
})
export class TransactionFormComponent implements OnInit {
    transactionForm!: FormGroup;
    transaction: Transaction | null;
    errorMessage = '';
    datesExpanded = false;
    singularResourceName: string;
    autocompleteFrom: Transaction | null;
    receipt: File | null;

    constructor(
        private router: Router,
        private route: ActivatedRoute,
        private formBuilder: FormBuilder,
        private ledgerService: LedgerService,
        private moneyPipe: MoneyPipe

    ) {
        this.singularResourceName = 'transaction';
        this.autocompleteFrom = null;
        this.receipt = null;
        this.transaction = null;
    }

    ngOnInit(): void {
        const id = Number(this.route.snapshot.paramMap.get('id') || 0)

        this.transactionForm = this.formBuilder.group({
            accounts: this.formBuilder.group({
                account: [null],
                destination: [null],
            }, {validators: atLeastOneAccount}),
            payee: ['', {validators: Validators.required}],
            amount: ['', {validators: [Validators.required, Validators.min(0.01)]}],
            dates: this.formBuilder.group({
                occurred_on: [this.today()],
                cleared_on: [null],
            }, {validators: dateRange}),
            tags: this.formBuilder.array([]),
            note: [null, {}],
        });

        this.ledgerService.getTransaction(id).subscribe(
            (transaction: Transaction) => this.populate(transaction)
        );

        this.amount.valueChanges.subscribe({
            next: (value) => {
                if (!value) return;
                this.amount.setValue(value.replace(/[^0-9.]/, ''), {emitEvent: false});
            },
        });

        if (id === 0) {
            this.payee.valueChanges.pipe(
                filter(value => value && value.length > 2),
                debounceTime(500),
                switchMap(payee => this.ledgerService.autocompletePayee(payee)),
            ).subscribe((result => this.autocomplete(result)));
        }
    }

    get account() { return this.accounts.controls['account'] as FormControl }
    get destination() { return this.accounts.controls['destination'] as FormControl }
    get payee() { return this.transactionForm.controls['payee'] }
    get amount() { return this.transactionForm.controls['amount'] }
    get accounts() { return this.transactionForm.controls['accounts'] as FormGroup }
    get dates() { return this.transactionForm.controls['dates'] as FormGroup }
    get occurredOn() { return this.dates.controls['occurred_on'] }
    get clearedOn() { return this.dates.controls['cleared_on'] }
    get note() { return this.transactionForm.controls['note'] }
    get tags() { return this.transactionForm.get('tags') as FormArray }

    autocomplete(searchResult: TransactionList) {
        if (searchResult.count === 0) {
            this.autocompleteFrom = null;
            return;
        }

        this.autocompleteFrom = Transaction.fromJson(searchResult.transactions[0]);
    }

    applyAutocompletedTransaction(e: MouseEvent) {
        e.preventDefault();
        if (!this.autocompleteFrom) {
            return;
        }

        while (this.tags.controls.length < this.autocompleteFrom.tags.length) {
            this.tagFieldPush('', false);
        }

        this.transactionForm.patchValue({
            account: this.autocompleteFrom.account || null,
            payee: this.autocompleteFrom.payee,
            amount: this.moneyPipe.transform(this.autocompleteFrom.amount, 'plain'),
            note: this.autocompleteFrom.note,
            tags: this.autocompleteFrom.tags,
        }, { emitEvent: false});

        this.autocompleteFrom = null;
    }

    tagFieldPush(value = '', markDirty = true) {
        this.tags.push(this.formBuilder.control(value));
        if (markDirty) {
            this.transactionForm.markAsDirty();
        }
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
            uid: transaction.uid,
            payee: transaction.payee,
            amount: this.moneyPipe.transform(transaction.amount, 'plain'),
            accounts: {
                account: transaction.account,
                destination: transaction.destination,
            },
            dates: {
                occurred_on: transaction.occurredOnYMD(),
                cleared_on: transaction.clearedOnYMD(),
            },
            note: transaction.note,
        });

        while (this.tags.controls.length < transaction.tags.length) {
            this.tagFieldPush('', false);
        }

        this.tags.patchValue(transaction.tags);

        if (transaction.account?.closed_on) {
            this.account.disable();
        } else {
            this.account.enable();
        }

        this.transaction = transaction;
        this.datesExpanded = (transaction.cleared_on instanceof Date);
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
            account: account,
        });
    }

    save(): void {
        if (!this.transactionForm.valid) {
            this.errorMessage = 'Cannot save because the form is incomplete.';
            return;
        }

        if (!this.transactionForm.dirty) {
            this.errorMessage = 'Cannot save because nothing has changed.';
            return;
        }

        if (!this.account.value && !this.destination.value) {
            this.errorMessage = 'Cannot save because an account has not been specified.';
            return;
        }

        const t = Transaction.clone(this.transaction!);

        t.account = this.account.value;
        t.destination = this.destination.value;
        t.payee = this.payee.value;
        t.amount = this.amount.value * 100;
        t.occurred_on = this.occurredOn.value;
        t.cleared_on = this.clearedOn.value || null;
        t.note = this.note.value;
        t.tags = this.tags.value;

        if (this.receipt) {
            t.receipt = this.receipt;
        }

        this.ledgerService.saveTransaction(t).subscribe({
            next: () => this.saved(),
            error: (err) => this.errorMessage = err,
        });
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

        this.ledgerService.deleteTransaction(this.transaction.uid).subscribe({
            next: () => this.deleted(),
            error: (err) => this.errorMessage = err,
        });
    }

    receiptChange(event: Event) {
        const files = (event.target as HTMLInputElement).files!;
        if (files.length > 0) {
            this.receipt = files[0];
            this.transactionForm.markAsDirty();
        }
    }
}
